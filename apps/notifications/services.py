import asyncio
import logging
from asgiref.sync import sync_to_async
from django.utils import timezone
from .models import NotificationLog, NotificationType

logger = logging.getLogger("apps.bot")


def log_notification(
    user,
    notification_type: str,
    message: str,
) -> NotificationLog:
    return NotificationLog.objects.create(
        user=user,
        notification_type=notification_type,
        message=message,
    )


async def send_telegram_message(telegram_id: int, text: str, parse_mode: str = "HTML") -> bool:
    from apps.bot.bot import get_bot
    bot = get_bot()
    if not bot:
        logger.error("Bot instance not available")
        return False
    try:
        await bot.send_message(telegram_id, text, parse_mode=parse_mode)
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message to {telegram_id}: {e}")
        return False


def send_notification_sync(user, notification_type: str, message: str) -> bool:
    """Send a Telegram notification from a synchronous context (Celery tasks, etc.).
    Never call this from inside an async function — use the anotify_* functions instead.
    """
    if not user.telegram_id:
        logger.warning(f"User {user.id} has no telegram_id, skipping notification")
        return False

    log = log_notification(user, notification_type, message)

    try:
        result = asyncio.run(send_telegram_message(user.telegram_id, message))
        if result:
            log.mark_sent()
            return True
        else:
            log.mark_failed("Send returned False")
            return False
    except Exception as e:
        log.mark_failed(str(e))
        logger.error(f"Notification send failed for user {user.id}: {e}")
        return False


def notify_task_assigned(task, assigned_user=None):
    if assigned_user and assigned_user.telegram_id:
        due_str = task.due_at.strftime("%d.%m.%Y %H:%M") if task.due_at else "Ko'rsatilmagan"
        message = (
            f"📋 <b>Yangi vazifa tayinlandi</b>\n\n"
            f"📌 <b>{task.title}</b>\n"
            f"📝 {task.description[:200]}\n\n"
            f"⚡️ Ustuvorlik: {task.get_priority_display()}\n"
            f"📅 Muddati: {due_str}\n\n"
            "Ko'rsatmalar mavjud. Vazifani ko'rish uchun /start buyrug'ini bering."
        )
        send_notification_sync(assigned_user, NotificationType.TASK_ASSIGNED, message)


def notify_report_submitted(report):
    task = report.task
    manager = None

    if task.assigned_department:
        from apps.users.services import get_department_head
        manager = get_department_head(task.assigned_department_id)

    if not manager:
        from apps.users.models import UserRole
        from apps.users.models import User
        manager = User.objects.filter(role=UserRole.BOSS, is_active=True).first()

    if manager and manager.telegram_id:
        message = (
            f"📊 <b>Yangi hisobot yuborildi</b>\n\n"
            f"👤 Xodim: {report.employee.get_display_name()}\n"
            f"📋 Vazifa: {task.title}\n"
            f"📅 Yuborilgan: {report.submitted_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Hisobotni ko'rish uchun /start buyrug'ini bering."
        )
        send_notification_sync(manager, NotificationType.REPORT_SUBMITTED, message)


def notify_report_accepted(report):
    employee = report.employee
    if employee.telegram_id:
        message = (
            f"✅ <b>Hisobotingiz qabul qilindi</b>\n\n"
            f"📋 Vazifa: {report.task.title}\n"
            f"📅 Qabul qilindi: {timezone.now().strftime('%d.%m.%Y %H:%M')}\n"
        )
        if report.manager_comment:
            message += f"💬 Izoh: {report.manager_comment}"
        send_notification_sync(employee, NotificationType.REPORT_ACCEPTED, message)


def notify_report_rejected(report):
    employee = report.employee
    if employee.telegram_id:
        comment = report.manager_comment or "Ko'rsatilmagan"
        message = (
            f"❌ <b>Hisobotingiz rad etildi</b>\n\n"
            f"📋 Vazifa: {report.task.title}\n"
            f"💬 Sabab: {comment}\n\n"
            "Hisobotni qayta yuborish uchun /start buyrug'ini bering."
        )
        send_notification_sync(employee, NotificationType.REPORT_REJECTED, message)


def notify_task_overdue(task, user):
    if user.telegram_id:
        message = (
            f"⚠️ <b>Vazifa muddati o'tdi</b>\n\n"
            f"📋 {task.title}\n"
            f"📅 Muddat: {task.due_at.strftime('%d.%m.%Y %H:%M') if task.due_at else '—'}\n\n"
            f"Iltimos, vazifani yangilang."
        )
        send_notification_sync(user, NotificationType.TASK_OVERDUE, message)


def notify_task_reminder(task, user):
    if user.telegram_id:
        message = (
            f"⏰ <b>Vazifa eslatmasi</b>\n\n"
            f"📋 {task.title}\n"
            f"📅 Muddat: {task.due_at.strftime('%d.%m.%Y %H:%M') if task.due_at else '—'}\n\n"
            f"Vazifani o'z vaqtida bajarishni unutmang!"
        )
        send_notification_sync(user, NotificationType.TASK_REMINDER, message)


# ---------------------------------------------------------------------------
# Async notification helpers — use ONLY inside async bot handlers.
# These await send_telegram_message() directly and log to DB via sync_to_async.
# ---------------------------------------------------------------------------

_alog_notification = sync_to_async(log_notification)


async def _asend_and_log(user, notification_type: str, message: str) -> None:
    """Create a DB log entry then fire the Telegram message, all inside async context."""
    log = await _alog_notification(user, notification_type, message)
    result = await send_telegram_message(user.telegram_id, message)
    if result:
        await sync_to_async(log.mark_sent)()
    else:
        await sync_to_async(log.mark_failed)("Send returned False")


async def anotify_task_assigned(task, assigned_user=None) -> None:
    if not assigned_user or not assigned_user.telegram_id:
        return
    due_str = task.due_at.strftime("%d.%m.%Y %H:%M") if task.due_at else "Ko'rsatilmagan"
    message = (
        f"📋 <b>Yangi vazifa tayinlandi</b>\n\n"
        f"📌 <b>{task.title}</b>\n"
        f"📝 {task.description[:200]}\n\n"
        f"⚡️ Ustuvorlik: {task.get_priority_display()}\n"
        f"📅 Muddati: {due_str}\n\n"
        "Ko'rsatmalar mavjud. Vazifani ko'rish uchun /start buyrug'ini bering."
    )
    try:
        await _asend_and_log(assigned_user, NotificationType.TASK_ASSIGNED, message)
    except Exception as e:
        logger.error(f"anotify_task_assigned failed for user {assigned_user.id}: {e}")


async def anotify_report_submitted(report) -> None:
    task = report.task
    manager = None

    if task.assigned_department_id:
        from apps.users.services import aget_department_head
        manager = await aget_department_head(task.assigned_department_id)

    if not manager:
        from apps.users.models import UserRole, User
        from asgiref.sync import sync_to_async
        manager = await sync_to_async(
            lambda: User.objects.filter(role=UserRole.BOSS, is_active=True).first()
        )()

    if not manager or not manager.telegram_id:
        return

    message = (
        f"📊 <b>Yangi hisobot yuborildi</b>\n\n"
        f"👤 Xodim: {report.employee.get_display_name()}\n"
        f"📋 Vazifa: {task.title}\n"
        f"📅 Yuborilgan: {report.submitted_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        "Hisobotni ko'rish uchun /start buyrug'ini bering."
    )
    try:
        await _asend_and_log(manager, NotificationType.REPORT_SUBMITTED, message)
    except Exception as e:
        logger.error(f"anotify_report_submitted failed: {e}")


async def anotify_report_accepted(report) -> None:
    employee = report.employee
    if not employee.telegram_id:
        return
    message = (
        f"✅ <b>Hisobotingiz qabul qilindi</b>\n\n"
        f"📋 Vazifa: {report.task.title}\n"
        f"📅 Qabul qilindi: {timezone.now().strftime('%d.%m.%Y %H:%M')}\n"
    )
    if report.manager_comment:
        message += f"💬 Izoh: {report.manager_comment}"
    try:
        await _asend_and_log(employee, NotificationType.REPORT_ACCEPTED, message)
    except Exception as e:
        logger.error(f"anotify_report_accepted failed for user {employee.id}: {e}")


async def anotify_report_rejected(report) -> None:
    employee = report.employee
    if not employee.telegram_id:
        return
    comment = report.manager_comment or "Ko'rsatilmagan"
    message = (
        f"❌ <b>Hisobotingiz rad etildi</b>\n\n"
        f"📋 Vazifa: {report.task.title}\n"
        f"💬 Sabab: {comment}\n\n"
        "Hisobotni qayta yuborish uchun /start buyrug'ini bering."
    )
    try:
        await _asend_and_log(employee, NotificationType.REPORT_REJECTED, message)
    except Exception as e:
        logger.error(f"anotify_report_rejected failed for user {employee.id}: {e}")
