"""
Report handlers.

Employee
  • Submit a text + optional media report against an active task
  • Triggered from main menu (menu:submit_report) or task-detail inline button

HEAD / BOSS
  • List pending (and all) reports
  • View full report
  • Accept / reject with optional comment

All navigation uses edit_html to replace the current message.
Cancel / Skip / Done actions are handled by inline-button callbacks — there
are no reply-keyboard text checks in state handlers.
"""
import logging

from telegram.loader import bot, handle
from core.sender import Sender
from telegram.keyboards.inlines import (
    report_list_inl, report_detail_inl,
    report_cb, page_cb, task_cb,
    task_report_select_inl, get_main_menu,
    wizard_cancel_inl, wizard_done_cancel_inl, wizard_skip_cancel_inl,
)
from telegram.states import ReportSubmitStates, ReportReviewStates
from apps.users.models import UserRole

logger = logging.getLogger("telegram.handlers")


# ---------------------------------------------------------------------------
# Task-detail "📊 Hisobot yuborish" callback (task already known)
# ---------------------------------------------------------------------------

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("task:") and ":report:" in c.data
)
async def cb_report_from_task(call):
    await bot.answer_callback_query(call.id)
    try:
        parsed  = task_cb.parse(call.data)
        task_id = int(parsed["task_id"])
    except Exception:
        return

    user = await Sender.get_db_user(call.from_user.id)
    if not user:
        return

    from apps.tasks.services import aget_task_instance
    task = await aget_task_instance(task_id)
    if not task:
        await Sender.send_html(call.message.chat.id, "❌ Vazifa topilmadi.")
        return

    await bot.set_state(call.from_user.id, ReportSubmitStates.entering_text, call.message.chat.id)
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data.clear()
        data["task_id"] = task_id

    await Sender.edit_html(
        call.message.chat.id, call.message.message_id,
        f"📊 <b>Hisobot yuborish</b>\n📋 Vazifa: <b>{task.title}</b>\n\n✍️ Hisobot matnini kiriting:",
        markup=wizard_cancel_inl("cancel_report"),
    )


# ---------------------------------------------------------------------------
# select_for_report callback (from task_report_select_inl)
# ---------------------------------------------------------------------------

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("task:") and ":select_for_report:" in c.data
)
async def cb_select_task_for_report(call):
    await bot.answer_callback_query(call.id)
    try:
        parsed  = task_cb.parse(call.data)
        task_id = int(parsed["task_id"])
    except Exception:
        return

    from apps.tasks.services import aget_task_instance
    task = await aget_task_instance(task_id)
    if not task:
        await Sender.send_html(call.message.chat.id, "❌ Vazifa topilmadi.")
        return

    await bot.set_state(call.from_user.id, ReportSubmitStates.entering_text, call.message.chat.id)
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data.clear()
        data["task_id"] = task_id

    await Sender.edit_html(
        call.message.chat.id, call.message.message_id,
        f"📊 <b>Hisobot yuborish</b>\n📋 Vazifa: <b>{task.title}</b>\n\n✍️ Hisobot matnini kiriting:",
        markup=wizard_cancel_inl("cancel_report"),
    )


@bot.callback_query_handler(func=lambda c: c.data == "cancel_report")
async def cb_cancel_report(call):
    await bot.answer_callback_query(call.id)
    await bot.delete_state(call.from_user.id, call.message.chat.id)
    user = await Sender.get_db_user(call.from_user.id)
    await Sender.edit_html(
        call.message.chat.id, call.message.message_id,
        "❌ Bekor qilindi.", markup=get_main_menu(user),
    )


# ---------------------------------------------------------------------------
# Report wizard — step 1: report text
# ---------------------------------------------------------------------------

@handle(state=ReportSubmitStates.entering_text)
async def state_report_text(sender):
    text = (sender.msg.text or "").strip()
    if not text:
        return
    if len(text) > 3000:
        await Sender.send_html(sender.chat_id, "❌ Matn 3000 belgidan oshmasligi kerak. Qaytadan:")
        return

    async with bot.retrieve_data(sender.user_id, sender.chat_id) as data:
        data["report_text"] = text

    await bot.set_state(sender.user_id, ReportSubmitStates.adding_media, sender.chat_id)
    await Sender.send_html(
        sender.chat_id,
        "📎 Rasm yoki fayl qo'shing (ixtiyoriy).\nTayyor bo'lgach <b>✅ Tayyor</b> tugmasini bosing:",
        markup=wizard_done_cancel_inl("done_report", "cancel_report"),
    )


# ---------------------------------------------------------------------------
# Report wizard — step 2: optional media
# ---------------------------------------------------------------------------

@handle(state=ReportSubmitStates.adding_media)
async def state_report_media(sender):
    msg = sender.msg

    if msg.photo:
        file_id = msg.photo[-1].file_id
        async with bot.retrieve_data(sender.user_id, sender.chat_id) as data:
            attachments = data.get("attachments", [])
            attachments.append({"type": "image", "file_id": file_id, "name": "photo.jpg"})
            data["attachments"] = attachments
        await Sender.send_html(
            sender.chat_id,
            "✅ Rasm qo'shildi. Yana qo'shing yoki '✅ Tayyor' tugmasini bosing.",
            markup=wizard_done_cancel_inl("done_report", "cancel_report"),
        )
        return

    if msg.document:
        file_id   = msg.document.file_id
        file_name = msg.document.file_name or "file"
        async with bot.retrieve_data(sender.user_id, sender.chat_id) as data:
            attachments = data.get("attachments", [])
            attachments.append({"type": "file", "file_id": file_id, "name": file_name})
            data["attachments"] = attachments
        await Sender.send_html(
            sender.chat_id,
            f"✅ Fayl qo'shildi: {file_name}",
            markup=wizard_done_cancel_inl("done_report", "cancel_report"),
        )
        return

    # Any other text or unsupported content — remind user
    await Sender.send_html(
        sender.chat_id,
        "📎 Rasm yoki fayl yuboring, yoki tugmani bosing.",
        markup=wizard_done_cancel_inl("done_report", "cancel_report"),
    )


@bot.callback_query_handler(func=lambda c: c.data == "done_report")
async def cb_done_report(call):
    await bot.answer_callback_query(call.id)
    state = await bot.get_state(call.from_user.id, call.message.chat.id)
    if state != ReportSubmitStates.adding_media.name:
        return
    await _finalize_report(call.from_user.id, call.message.chat.id)


# ---------------------------------------------------------------------------
# Report submission — finalize
# ---------------------------------------------------------------------------

async def _finalize_report(user_id: int, chat_id: int):
    async with bot.retrieve_data(user_id, chat_id) as data:
        task_id     = data.get("task_id")
        report_text = data.get("report_text", "")
        attachments = data.get("attachments", [])

    await bot.delete_state(user_id, chat_id)

    user = await Sender.get_db_user(user_id)
    if not user:
        await Sender.send_html(chat_id, "❌ Foydalanuvchi topilmadi.")
        return

    from apps.tasks.services import aget_task_instance
    task = await aget_task_instance(task_id)
    if not task:
        await Sender.send_html(chat_id, "❌ Vazifa topilmadi.")
        return

    try:
        from apps.reports.services import acreate_report, aadd_attachment_from_file
        report = await acreate_report(task=task, employee=user, text=report_text)

        for att in attachments:
            try:
                file_info  = await bot.get_file(att["file_id"])
                downloaded = await bot.download_file(file_info.file_path)
                from apps.reports.models import FileType
                file_type  = FileType.IMAGE if att["type"] == "image" else FileType.FILE
                await aadd_attachment_from_file(
                    report=report,
                    file_content=downloaded,
                    original_name=att["name"],
                    file_type=file_type,
                    telegram_file_id=att["file_id"],
                )
            except Exception as exc:
                logger.warning("Attachment save failed: %s", exc)

        from apps.notifications.services import anotify_report_submitted
        await anotify_report_submitted(report)

        await Sender.send_html(
            chat_id,
            "✅ <b>Hisobot muvaffaqiyatli yuborildi!</b>",
            markup=get_main_menu(user),
        )

    except (PermissionError, ValueError) as exc:
        await Sender.send_html(chat_id, f"❌ {exc}", markup=get_main_menu(user))
    except Exception as exc:
        logger.error("Report submission failed: %s", exc)
        await Sender.send_html(chat_id, "❌ Hisobot yuborishda xatolik yuz berdi.", markup=get_main_menu(user))


# ---------------------------------------------------------------------------
# Report list (manager view)
# ---------------------------------------------------------------------------

async def _show_reports_list(
    chat_id: int,
    manager,
    page: int,
    mode: str,
    edit_msg_id: int | None = None,
):
    from apps.reports.services import aget_pending_reports_for_manager, aget_all_reports

    if mode == "pending":
        reports = await aget_pending_reports_for_manager(manager)
        title   = "📊 Tekshirish kutayotgan hisobotlar"
    else:
        reports = await aget_all_reports()
        title   = "📊 Barcha hisobotlar"

    if not reports:
        text = f"{title}\n\n📭 Hisobotlar topilmadi."
        if edit_msg_id:
            await Sender.edit_html(chat_id, edit_msg_id, text)
        else:
            await Sender.send_html(chat_id, text)
        return

    page_items, total_pages, page = Sender.paginate(reports, page)
    markup = report_list_inl(page_items, page, total_pages, mode)
    text   = f"{title} ({len(reports)} ta)"
    if edit_msg_id:
        await Sender.edit_html(chat_id, edit_msg_id, text, markup)
    else:
        await Sender.send_html(chat_id, text, markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("pg:reports:"))
async def cb_report_page(call):
    await bot.answer_callback_query(call.id)
    try:
        parsed = page_cb.parse(call.data)
        page   = int(parsed["page"])
        mode   = parsed["flt"]
    except Exception:
        return

    user = await Sender.get_db_user(call.from_user.id)
    if not user:
        return

    from apps.reports.services import aget_pending_reports_for_manager, aget_all_reports
    reports = (
        await aget_pending_reports_for_manager(user)
        if mode == "pending"
        else await aget_all_reports()
    )

    if not reports:
        await Sender.edit_html(call.message.chat.id, call.message.message_id, "📭 Hisobotlar topilmadi.")
        return

    page_items, total_pages, page = Sender.paginate(reports, page)
    markup = report_list_inl(page_items, page, total_pages, mode)
    await Sender.edit_html(
        call.message.chat.id, call.message.message_id,
        f"📊 Hisobotlar ({len(reports)} ta)", markup,
    )


@bot.callback_query_handler(func=lambda c: c.data == "back_to_reports")
async def cb_back_to_reports(call):
    await bot.answer_callback_query(call.id)
    user = await Sender.get_db_user(call.from_user.id)
    if user:
        await _show_reports_list(
            call.message.chat.id, user, page=0, mode="pending",
            edit_msg_id=call.message.message_id,
        )


# ---------------------------------------------------------------------------
# Report detail view
# ---------------------------------------------------------------------------

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("report:") and ":view:" in c.data
)
async def cb_report_view(call):
    await bot.answer_callback_query(call.id)
    try:
        parsed    = report_cb.parse(call.data)
        report_id = int(parsed["report_id"])
    except Exception:
        return

    user = await Sender.get_db_user(call.from_user.id)
    if not user:
        return

    from apps.reports.services import aget_report_by_id
    report = await aget_report_by_id(report_id)
    if not report:
        await Sender.send_html(call.message.chat.id, "❌ Hisobot topilmadi.")
        return

    can_review = user.role in [UserRole.BOSS, UserRole.HEAD]
    text       = Sender.format_report(report)
    markup     = report_detail_inl(report, can_review=can_review)
    await Sender.edit_html(call.message.chat.id, call.message.message_id, text, markup)


# ---------------------------------------------------------------------------
# Accept report
# ---------------------------------------------------------------------------

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("report:") and ":accept:" in c.data
)
async def cb_report_accept(call):
    await bot.answer_callback_query(call.id)
    try:
        parsed    = report_cb.parse(call.data)
        report_id = int(parsed["report_id"])
    except Exception:
        return

    user = await Sender.require_role(call.from_user.id, call.message.chat.id, UserRole.BOSS, UserRole.HEAD)
    if not user:
        return

    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data["review_report_id"] = report_id
        data["review_action"]    = "accept"

    await bot.set_state(
        call.from_user.id, ReportReviewStates.entering_accept_comment, call.message.chat.id
    )
    await Sender.edit_html(
        call.message.chat.id, call.message.message_id,
        "💬 Qabul izohi kiriting (ixtiyoriy):",
        markup=wizard_skip_cancel_inl("skip_accept_comment", "cancel_review"),
    )


@handle(state=ReportReviewStates.entering_accept_comment)
async def state_accept_comment(sender):
    comment = (sender.msg.text or "").strip()
    # Any non-empty text is treated as the accept comment
    await _do_accept_report(sender.user_id, sender.chat_id, comment)


@bot.callback_query_handler(func=lambda c: c.data == "skip_accept_comment")
async def cb_skip_accept_comment(call):
    await bot.answer_callback_query(call.id)
    if await bot.get_state(call.from_user.id, call.message.chat.id) != ReportReviewStates.entering_accept_comment.name:
        return
    await Sender.edit_html(call.message.chat.id, call.message.message_id, "⏳ Qayta ko'rilmoqda...")
    await _do_accept_report(call.from_user.id, call.message.chat.id, comment="")


async def _do_accept_report(user_id: int, chat_id: int, comment: str):
    async with bot.retrieve_data(user_id, chat_id) as data:
        report_id = data.get("review_report_id")
    await bot.delete_state(user_id, chat_id)

    user = await Sender.get_db_user(user_id)
    from apps.reports.services import aget_report_by_id, aaccept_report
    report = await aget_report_by_id(report_id)
    if not report:
        await Sender.send_html(chat_id, "❌ Hisobot topilmadi.")
        return

    try:
        await aaccept_report(report, user, comment)
        from apps.notifications.services import anotify_report_accepted
        await anotify_report_accepted(report)
        await Sender.send_html(chat_id, "✅ Hisobot qabul qilindi.", markup=get_main_menu(user))
    except Exception as exc:
        logger.error("Report accept failed: %s", exc)
        await Sender.send_html(chat_id, "❌ Xatolik yuz berdi.")


# ---------------------------------------------------------------------------
# Reject report
# ---------------------------------------------------------------------------

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("report:") and ":reject:" in c.data
)
async def cb_report_reject(call):
    await bot.answer_callback_query(call.id)
    try:
        parsed    = report_cb.parse(call.data)
        report_id = int(parsed["report_id"])
    except Exception:
        return

    user = await Sender.require_role(call.from_user.id, call.message.chat.id, UserRole.BOSS, UserRole.HEAD)
    if not user:
        return

    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data["review_report_id"] = report_id
        data["review_action"]    = "reject"

    await bot.set_state(
        call.from_user.id, ReportReviewStates.entering_reject_reason, call.message.chat.id
    )
    await Sender.edit_html(
        call.message.chat.id, call.message.message_id,
        "💬 Rad etish sababini kiriting (majburiy):",
        markup=wizard_cancel_inl("cancel_review"),
    )


@handle(state=ReportReviewStates.entering_reject_reason)
async def state_reject_reason(sender):
    text = (sender.msg.text or "").strip()
    if not text:
        await Sender.send_html(sender.chat_id, "❌ Sabab bo'sh bo'lmasligi kerak.")
        return

    async with bot.retrieve_data(sender.user_id, sender.chat_id) as data:
        report_id = data.get("review_report_id")
    await bot.delete_state(sender.user_id, sender.chat_id)

    user = await Sender.get_db_user(sender.user_id)
    from apps.reports.services import aget_report_by_id, areject_report
    report = await aget_report_by_id(report_id)
    if not report:
        await Sender.send_html(sender.chat_id, "❌ Hisobot topilmadi.")
        return

    try:
        await areject_report(report, user, text)
        from apps.notifications.services import anotify_report_rejected
        await anotify_report_rejected(report)
        await Sender.send_html(sender.chat_id, "❌ Hisobot rad etildi.", markup=get_main_menu(user))
    except Exception as exc:
        logger.error("Report reject failed: %s", exc)
        await Sender.send_html(sender.chat_id, "❌ Xatolik yuz berdi.")


@bot.callback_query_handler(func=lambda c: c.data == "cancel_review")
async def cb_cancel_review(call):
    await bot.answer_callback_query(call.id)
    await bot.delete_state(call.from_user.id, call.message.chat.id)
    user = await Sender.get_db_user(call.from_user.id)
    await Sender.edit_html(
        call.message.chat.id, call.message.message_id,
        "❌ Bekor qilindi.", markup=get_main_menu(user),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _start_report_flow(chat_id: int, user_id: int, user):
    """Show active-task picker. Called from commands.py menu dispatcher."""
    from apps.tasks.services import aget_active_tasks_for_user
    tasks = await aget_active_tasks_for_user(user)
    if not tasks:
        await Sender.send_html(chat_id, "📭 Hisobot yuborish uchun faol vazifalar yo'q.")
        return

    await bot.set_state(user_id, ReportSubmitStates.choosing_task, chat_id)
    await Sender.send_html(chat_id, "📋 Qaysi vazifa uchun hisobot?", markup=task_report_select_inl(tasks))
