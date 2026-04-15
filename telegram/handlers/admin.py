"""
Admin / management handlers (BOSS role).

Features
--------
• Statistics      — global summary across all departments
• Broadcast       — compose & confirm a message sent to every active user
• Users list      — paginated list of all users with basic info

Internal helpers (_show_statistics, _start_broadcast, _show_users_list) are
called by commands.py menu dispatcher so they must remain importable.
"""
import asyncio
import logging

from telegram.loader import bot, handle
from core.sender import Sender
from telegram.keyboards.inlines import (
    confirm_broadcast_inl,
    users_list_inl,
    user_detail_inl,
    user_role_picker_inl,
    user_dept_picker_inl,
    admin_user_cb,
    admin_setrole_cb,
    admin_setdept_cb,
    page_cb,
    wizard_cancel_inl,
    get_main_menu,
)

from telegram.states import AdminBroadcastStates
from apps.users.models import UserRole

logger = logging.getLogger("telegram.handlers")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

async def _show_statistics(chat_id: int, edit_msg_id: int | None = None) -> None:
    from apps.departments.services import aget_global_summary
    stats = await aget_global_summary()
    text  = Sender.format_statistics(stats)
    if edit_msg_id:
        await Sender.edit_html(chat_id, edit_msg_id, text)
    else:
        await Sender.send_html(chat_id, text)


# ---------------------------------------------------------------------------
# Users list
# ---------------------------------------------------------------------------

async def _show_users_list(
    chat_id: int,
    page: int = 0,
    edit_msg_id: int | None = None,
) -> None:
    from asgiref.sync import sync_to_async
    from apps.users.models import User

    users = await sync_to_async(
        lambda: list(
            User.objects.filter(is_active=True)
            .select_related("department")
            .order_by("role", "full_name")
        )
    )()

    if not users:
        text = "📭 Foydalanuvchilar topilmadi."
        if edit_msg_id:
            await Sender.edit_html(chat_id, edit_msg_id, text)
        else:
            await Sender.send_html(chat_id, text)
        return

    page_items, total_pages, page = Sender.paginate(users, page, per_page=8)
    markup = users_list_inl(page_items, page, total_pages)
    text   = f"👥 Foydalanuvchilar ({len(users)} ta)"
    if edit_msg_id:
        await Sender.edit_html(chat_id, edit_msg_id, text, markup)
    else:
        await Sender.send_html(chat_id, text, markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("pg:users:"))
async def cb_users_page(call):
    await bot.answer_callback_query(call.id)
    user = await Sender.require_role(call.from_user.id, call.message.chat.id, UserRole.BOSS)
    if not user:
        return
    try:
        parsed = page_cb.parse(call.data)
        page   = int(parsed["page"])
    except Exception:
        return
    await _show_users_list(call.message.chat.id, page=page, edit_msg_id=call.message.message_id)


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("auser:") and ":view:" in c.data
)
async def cb_user_view(call):
    await bot.answer_callback_query(call.id)
    user = await Sender.require_role(call.from_user.id, call.message.chat.id, UserRole.BOSS)
    if not user:
        return
    try:
        parsed    = admin_user_cb.parse(call.data)
        target_id = int(parsed["user_id"])
    except Exception:
        return

    from asgiref.sync import sync_to_async
    from apps.users.models import User as DjUser

    target = await sync_to_async(
        lambda: DjUser.objects.filter(id=target_id).select_related("department").first()
    )()
    if not target:
        await bot.answer_callback_query(call.id, "Foydalanuvchi topilmadi.", show_alert=True)
        return

    role_icons = {"boss": "👑", "head": "🏅", "employee": "👤"}
    icon       = role_icons.get(target.role or "", "👤")
    role_label = target.get_role_display() if target.has_role else "Tayinlanmagan"
    dept       = target.department.name if target.department else "—"

    text = (
        f"{icon} <b>{target.get_display_name()}</b>\n\n"
        f"🔑 Login: @{target.username}\n"
        f"📱 Telefon: {target.phone_number or '—'}\n"
        f"🎭 Rol: <b>{role_label}</b>\n"
        f"🏢 Bo'lim: {dept}\n"
        f"📅 Ro'yxatdan: {target.created_at.strftime('%d.%m.%Y')}\n"
        f"🔗 Telegram ID: <code>{target.telegram_id or '—'}</code>"
    )
    await Sender.edit_html(call.message.chat.id, call.message.message_id, text, markup=user_detail_inl(target.id))


@bot.callback_query_handler(func=lambda c: c.data == "back_to_users")
async def cb_back_to_users(call):
    await bot.answer_callback_query(call.id)
    await _show_users_list(call.message.chat.id, page=0, edit_msg_id=call.message.message_id)


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("auser:") and ":role:" in c.data
)
async def cb_user_role_picker(call):
    await bot.answer_callback_query(call.id)
    admin = await Sender.require_role(call.from_user.id, call.message.chat.id, UserRole.BOSS)
    if not admin:
        return
    try:
        parsed    = admin_user_cb.parse(call.data)
        target_id = int(parsed["user_id"])
    except Exception:
        return

    from asgiref.sync import sync_to_async
    from apps.users.models import User as DjUser
    target = await sync_to_async(
        lambda: DjUser.objects.filter(id=target_id).select_related("department").first()
    )()
    if not target:
        await bot.answer_callback_query(call.id, "Foydalanuvchi topilmadi.", show_alert=True)
        return

    role_label = target.get_role_display() if target.has_role else "Tayinlanmagan"
    text = (
        f"🎭 <b>{target.get_display_name()}</b> uchun rol tanlang\n\n"
        f"Joriy rol: <b>{role_label}</b>"
    )
    await Sender.edit_html(
        call.message.chat.id, call.message.message_id, text,
        markup=user_role_picker_inl(target_id),
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("auser_setrole:"))
async def cb_user_setrole(call):
    await bot.answer_callback_query(call.id)
    admin = await Sender.require_role(call.from_user.id, call.message.chat.id, UserRole.BOSS)
    if not admin:
        return
    try:
        parsed    = admin_setrole_cb.parse(call.data)
        target_id = int(parsed["user_id"])
        role      = parsed["role"]
    except Exception:
        return

    if role == "boss":
        # No department needed — assign directly
        from apps.users.services import set_user_role
        target = await set_user_role(target_id, role)
        await _notify_role_assigned(target, role, department=None)
        await Sender.edit_html(
            call.message.chat.id, call.message.message_id,
            f"✅ <b>{target.get_display_name()}</b> ga <b>Boss</b> roli tayinlandi.",
            markup=user_detail_inl(target_id),
        )
        return

    # HEAD or EMPLOYEE — need department selection
    from asgiref.sync import sync_to_async
    from apps.departments.models import Department
    departments = await sync_to_async(
        lambda: list(Department.objects.filter(is_active=True).order_by("name"))
    )()
    if not departments:
        await bot.answer_callback_query(call.id, "Hech qanday bo'lim topilmadi.", show_alert=True)
        return

    role_labels = {"head": "Bo'lim boshlig'i", "employee": "Ishchi"}
    text = (
        f"🏢 <b>{role_labels.get(role, role)}</b> uchun bo'lim tanlang:"
    )
    await Sender.edit_html(
        call.message.chat.id, call.message.message_id, text,
        markup=user_dept_picker_inl(target_id, role, departments),
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("auser_dept:"))
async def cb_user_setdept(call):
    await bot.answer_callback_query(call.id)
    admin = await Sender.require_role(call.from_user.id, call.message.chat.id, UserRole.BOSS)
    if not admin:
        return
    try:
        parsed    = admin_setdept_cb.parse(call.data)
        target_id = int(parsed["user_id"])
        role      = parsed["role"]
        dept_id   = int(parsed["dept_id"])
    except Exception:
        return

    from apps.users.services import set_user_role
    from apps.departments.models import Department
    from asgiref.sync import sync_to_async

    target = await set_user_role(target_id, role, department_id=dept_id)
    dept   = await sync_to_async(lambda: Department.objects.get(pk=dept_id))()
    await _notify_role_assigned(target, role, department=dept)

    role_labels = {"head": "Bo'lim boshlig'i", "employee": "Ishchi"}
    await Sender.edit_html(
        call.message.chat.id, call.message.message_id,
        f"✅ <b>{target.get_display_name()}</b> ga "
        f"<b>{role_labels.get(role, role)}</b> roli tayinlandi. "
        f"Bo'lim: <b>{dept.name}</b>",
        markup=user_detail_inl(target_id),
    )


async def _notify_role_assigned(target, role: str, department) -> None:
    """Send a Telegram notification to the target user about their new role."""
    if not target.telegram_id:
        return
    role_labels = {"boss": "👑 Boss", "head": "🏅 Bo'lim boshlig'i", "employee": "👤 Ishchi"}
    dept_line   = f"\n🏢 Bo'lim: <b>{department.name}</b>" if department else ""
    text = (
        f"🎉 Sizga yangi rol tayinlandi!\n\n"
        f"🎭 Rol: <b>{role_labels.get(role, role)}</b>{dept_line}\n\n"
        "Yangi imkoniyatlardan foydalanish uchun /start bosing."
    )
    try:
        await Sender.send_html(target.telegram_id, text)
    except Exception as exc:
        logger.warning("Role notification failed for %s: %s", target.telegram_id, exc)


# ---------------------------------------------------------------------------
# Broadcast
# ---------------------------------------------------------------------------

async def _start_broadcast(chat_id: int, user_id: int) -> None:
    """Entry point for broadcast wizard — called from menu dispatcher."""
    await bot.set_state(user_id, AdminBroadcastStates.entering_message, chat_id)
    await Sender.send_html(
        chat_id,
        "📢 <b>Xabar yuborish</b>\n\n✍️ Yubormoqchi bo'lgan xabaringizni kiriting:",
        markup=wizard_cancel_inl("cancel_broadcast"),
    )


@handle(state=AdminBroadcastStates.entering_message)
async def state_broadcast_message(sender):
    text = (sender.msg.text or "").strip()
    if not text:
        await Sender.send_html(sender.chat_id, "❌ Xabar bo'sh bo'lmasligi kerak.")
        return

    async with bot.retrieve_data(sender.user_id, sender.chat_id) as data:
        data["broadcast_message"] = text

    preview      = text[:500] + ("..." if len(text) > 500 else "")
    confirm_text = (
        f"📢 Ushbu xabarni <b>barcha faol foydalanuvchilarga</b> yuboryapsizmi?\n\n"
        f"<blockquote>{preview}</blockquote>"
    )
    await bot.set_state(sender.user_id, AdminBroadcastStates.confirming, sender.chat_id)
    await Sender.send_html(sender.chat_id, confirm_text, markup=confirm_broadcast_inl())


@bot.callback_query_handler(func=lambda c: c.data == "cancel_broadcast")
async def cb_cancel_broadcast(call):
    await bot.answer_callback_query(call.id)
    await bot.delete_state(call.from_user.id, call.message.chat.id)
    user = await Sender.get_db_user(call.from_user.id)
    await Sender.edit_html(
        call.message.chat.id, call.message.message_id,
        "❌ Bekor qilindi.", markup=get_main_menu(user),
    )


@bot.callback_query_handler(func=lambda c: c.data in ("broadcast:confirm", "broadcast:cancel"))
async def cb_broadcast_confirm(call):
    await bot.answer_callback_query(call.id)
    state = await bot.get_state(call.from_user.id, call.message.chat.id)
    if state != AdminBroadcastStates.confirming.name:
        return

    if call.data == "broadcast:cancel":
        await bot.delete_state(call.from_user.id, call.message.chat.id)
        user = await Sender.get_db_user(call.from_user.id)
        await Sender.edit_html(
            call.message.chat.id, call.message.message_id,
            "❌ Bekor qilindi.", markup=get_main_menu(user),
        )
        return

    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        message_text = data.get("broadcast_message", "")

    await bot.delete_state(call.from_user.id, call.message.chat.id)
    await Sender.edit_html(call.message.chat.id, call.message.message_id, "⏳ Xabar yuborilmoqda...")

    from asgiref.sync import sync_to_async
    from apps.users.models import User as DjUser
    recipients = await sync_to_async(
        lambda: list(
            DjUser.objects.filter(is_active=True).exclude(telegram_id__isnull=True)
            .values_list("telegram_id", flat=True)
        )
    )()

    sent   = 0
    failed = 0
    for tg_id in recipients:
        try:
            await bot.send_message(
                tg_id,
                f"📢 <b>Xabar</b>\n\n{message_text}",
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as exc:
            logger.warning("Broadcast failed for %s: %s", tg_id, exc)
            failed += 1

    result_text = f"✅ Xabar <b>{sent}</b> foydalanuvchiga yuborildi."
    if failed:
        result_text += f"\n⚠️ {failed} ta foydalanuvchiga yuborib bo'lmadi."

    user = await Sender.get_db_user(call.from_user.id)
    await Sender.send_html(call.message.chat.id, result_text, markup=get_main_menu(user))
    logger.info("Broadcast by %s: sent=%d failed=%d", call.from_user.id, sent, failed)
