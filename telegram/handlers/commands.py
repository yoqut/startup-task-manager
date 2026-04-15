"""
Global command handlers and main-menu inline dispatcher.

/start, /help, /profile, /tasks, /cancel  — work for every role.
menu:* callback — dispatches inline main-menu button presses.

All navigation triggered by inline buttons uses Sender.edit_html to replace
the current message instead of sending a new one.
"""
import logging

from telegram.loader import bot, handle
from telegram.keyboards.inlines import get_main_menu
from core.sender import Sender

logger = logging.getLogger("telegram.handlers")


# ---------------------------------------------------------------------------
# Shared display helpers
# ---------------------------------------------------------------------------

async def _show_help(chat_id: int, edit_msg_id: int | None = None) -> None:
    text = (
        "❓ <b>Yordam</b>\n\n"
        "<b>Buyruqlar:</b>\n"
        "/start — Asosiy menyuga qaytish\n"
        "/tasks — Vazifalar ro'yxati\n"
        "/profile — Profil ma'lumotlari\n"
        "/cancel — Amalni bekor qilish\n"
        "/help — Ushbu yordam xabari\n\n"
        "Savollar bo'lsa administrator bilan bog'laning."
    )
    if edit_msg_id:
        await Sender.edit_html(chat_id, edit_msg_id, text)
    else:
        await Sender.send_html(chat_id, text)


async def _show_profile(chat_id: int, user_id: int, edit_msg_id: int | None = None) -> None:
    user = await Sender.get_db_user(user_id)
    if not user:
        await Sender.send_html(chat_id, "❌ Foydalanuvchi topilmadi. /start bosing.")
        return
    role_text  = user.get_role_display() if user.has_role else "Tayinlanmagan"
    dept_text  = user.department.name if user.department else "—"
    phone_text = user.phone_number or "—"
    text = (
        f"👤 <b>Profil</b>\n\n"
        f"📛 Ism: <b>{user.full_name or user.username}</b>\n"
        f"🔑 Login: @{user.username}\n"
        f"📱 Telefon: {phone_text}\n"
        f"🎭 Rol: <b>{role_text}</b>\n"
        f"🏢 Bo'lim: {dept_text}\n"
        f"📅 Ro'yxatdan o'tgan: {user.created_at.strftime('%d.%m.%Y')}"
    )
    if edit_msg_id:
        await Sender.edit_html(chat_id, edit_msg_id, text)
    else:
        await Sender.send_html(chat_id, text)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

@handle(commands=["start"])
async def cmd_start(sender: Sender):
    tg_user = sender.user
    await bot.delete_state(tg_user.id, sender.chat_id)

    from apps.users.services import get_or_create_user_by_telegram
    user, is_new = await get_or_create_user_by_telegram(
        telegram_id=tg_user.id,
        username=getattr(tg_user, "username", "") or "",
        full_name=getattr(tg_user, "full_name", "") or "",
    )

    name = user.full_name or user.username
    if is_new:
        text = (
            f"👋 Xush kelibsiz, <b>{name}</b>!\n\n"
            "Siz tizimga muvaffaqiyatli qo'shildingiz. ✅\n\n"
            "Administrator sizga rol tayinlagandan so'ng "
            "to'liq funksionallikdan foydalana olasiz."
        )
    else:
        role_label = f" <i>({user.get_role_display()})</i>" if user.has_role else ""
        text = f"👋 Xush kelibsiz, <b>{name}</b>{role_label}!\n\nAsosiy menyu:"

    from telebot.types import ReplyKeyboardRemove
    await bot.send_message(sender.chat_id, "·", reply_markup=ReplyKeyboardRemove())
    await Sender.send_html(sender.chat_id, text, markup=get_main_menu(user))


# ---------------------------------------------------------------------------
# /help, /profile
# ---------------------------------------------------------------------------

@handle(commands=["help"])
async def cmd_help(sender: Sender):
    await _show_help(sender.chat_id)


@handle(commands=["profile"])
async def cmd_profile(sender: Sender):
    await _show_profile(sender.chat_id, sender.user_id)


# ---------------------------------------------------------------------------
# /tasks
# ---------------------------------------------------------------------------

@handle(commands=["tasks"])
async def cmd_tasks(sender: Sender):
    from telegram.handlers.tasks import show_task_list
    user = await Sender.get_db_user(sender.user_id)
    if not user or not user.has_role:
        await Sender.send_html(sender.chat_id, "⚠️ Sizga hali rol tayinlanmagan.")
        return
    await show_task_list(sender.chat_id, sender.user_id, user)


# ---------------------------------------------------------------------------
# /cancel
# ---------------------------------------------------------------------------

@handle(commands=["cancel"])
async def cmd_cancel(sender: Sender):
    state = await bot.get_state(sender.user_id, sender.chat_id)
    if state:
        await bot.delete_state(sender.user_id, sender.chat_id)
        await Sender.send_html(sender.chat_id, "❌ Amal bekor qilindi.")
    else:
        await Sender.send_html(sender.chat_id, "❌ Bekor qilinadigan amal yo'q.")
    user = await Sender.get_db_user(sender.user_id)
    await Sender.send_html(sender.chat_id, "Asosiy menyu:", markup=get_main_menu(user))


# ---------------------------------------------------------------------------
# Inline main-menu dispatcher  (menu:* callbacks)
# ---------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda c: c.data.startswith("menu:"))
async def cb_menu_dispatch(call):
    await bot.answer_callback_query(call.id)
    action      = call.data.split(":", 1)[1]
    chat_id     = call.message.chat.id
    user_id     = call.from_user.id
    edit_msg_id = call.message.message_id

    if action == "help":
        await _show_help(chat_id, edit_msg_id=edit_msg_id)
        return

    if action == "profile":
        await _show_profile(chat_id, user_id, edit_msg_id=edit_msg_id)
        return

    user = await Sender.get_db_user(user_id)

    if action == "tasks":
        if not user or not user.has_role:
            await Sender.edit_html(chat_id, edit_msg_id, "⚠️ Sizga hali rol tayinlanmagan.")
            return
        from telegram.handlers.tasks import show_task_list
        await show_task_list(chat_id, user_id, user, edit_message_id=edit_msg_id)
        return

    if action == "new_task":
        from telegram.handlers.tasks import _start_new_task
        from apps.users.models import UserRole
        u = await Sender.require_role(user_id, chat_id, UserRole.BOSS, UserRole.HEAD)
        if u:
            await _start_new_task(chat_id, user_id, u)
        return

    if action == "submit_report":
        if not user or not user.has_role:
            await Sender.edit_html(chat_id, edit_msg_id, "⚠️ Sizga hali rol tayinlanmagan.")
            return
        from telegram.handlers.reports import _start_report_flow
        await _start_report_flow(chat_id, user_id, user)
        return

    if action == "reports":
        from telegram.handlers.reports import _show_reports_list
        from apps.users.models import UserRole
        u = await Sender.require_role(user_id, chat_id, UserRole.HEAD, UserRole.BOSS)
        if u:
            mode = "all" if u.role == UserRole.BOSS else "pending"
            await _show_reports_list(chat_id, u, page=0, mode=mode, edit_msg_id=edit_msg_id)
        return

    if action == "department":
        from apps.users.models import UserRole
        u = await Sender.require_role(user_id, chat_id, UserRole.HEAD)
        if not u or not u.department_id:
            await Sender.edit_html(chat_id, edit_msg_id, "❌ Bo'lim topilmadi.")
            return
        from apps.departments.services import aget_department_summary
        summary = await aget_department_summary(u.department_id)
        await Sender.edit_html(chat_id, edit_msg_id, Sender.format_department_summary(summary))
        return

    if action == "users":
        from telegram.handlers.admin import _show_users_list
        from apps.users.models import UserRole
        u = await Sender.require_role(user_id, chat_id, UserRole.BOSS)
        if u:
            await _show_users_list(chat_id, edit_msg_id=edit_msg_id)
        return

    if action == "broadcast":
        from telegram.handlers.admin import _start_broadcast
        from apps.users.models import UserRole
        u = await Sender.require_role(user_id, chat_id, UserRole.BOSS)
        if u:
            await _start_broadcast(chat_id, user_id)
        return

    if action == "statistics":
        from telegram.handlers.admin import _show_statistics
        from apps.users.models import UserRole
        u = await Sender.require_role(user_id, chat_id, UserRole.BOSS)
        if u:
            await _show_statistics(chat_id, edit_msg_id=edit_msg_id)
        return


# ---------------------------------------------------------------------------
# back_to_main
# ---------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda c: c.data == "back_to_main")
async def cb_back_to_main(call):
    await bot.answer_callback_query(call.id)
    user = await Sender.get_db_user(call.from_user.id)
    await Sender.edit_html(
        call.message.chat.id, call.message.message_id,
        "🏠 Asosiy menyu:", markup=get_main_menu(user),
    )


# ---------------------------------------------------------------------------
# noop
# ---------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda c: c.data == "noop")
async def cb_noop(call):
    await bot.answer_callback_query(call.id)
