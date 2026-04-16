"""
Notification Services — Multi-channel dispatch.
All notification sending flows through here.
"""
import logging
from django.utils import timezone

logger = logging.getLogger("apps.notifications")


def dispatch_agent_notification(company, title: str, body: str, agent_type: str, priority: str = "medium"):
    """
    Send a notification from an agent to all managers and owners in the company.
    Dispatches to Telegram + creates in-app notification record.
    """
    from apps.notifications.models import Notification
    from django.contrib.auth import get_user_model
    User = get_user_model()

    recipients = User.objects.filter(
        company=company,
        is_active=True,
        role__in=["owner", "admin", "manager"],
    )

    for user in recipients:
        notification = Notification.objects.create(
            company=company,
            recipient=user,
            channel=Notification.Channel.IN_APP,
            priority=priority,
            title=title,
            body=body,
            ref_type="agent_execution",
            ref_id=agent_type,
        )

        if user.notify_via_telegram and user.telegram_user_id:
            _send_telegram_message.delay(
                telegram_user_id=user.telegram_user_id,
                message=f"*{title}*\n\n{body}",
                notification_id=str(notification.id),
            )


def dispatch_approval_notification(company, approval):
    """
    Notify all eligible approvers about a pending approval request.
    Sends Telegram message with inline approve/reject buttons.
    """
    from apps.notifications.models import Notification
    from django.contrib.auth import get_user_model
    User = get_user_model()

    approvers = User.objects.filter(
        company=company,
        is_active=True,
        role__in=["owner", "admin", "manager"],
    )

    for user in approvers:
        notification = Notification.objects.create(
            company=company,
            recipient=user,
            channel=Notification.Channel.IN_APP,
            priority=Notification.Priority.HIGH,
            title=f"Approval Required: {approval.title}",
            body=f"Confidence: {approval.confidence_score:.0%}\n\n{approval.reasoning}",
            ref_type="approval_request",
            ref_id=str(approval.id),
        )

        if user.notify_via_telegram and user.telegram_user_id:
            _send_telegram_approval.delay(
                telegram_user_id=user.telegram_user_id,
                approval_id=str(approval.id),
                notification_id=str(notification.id),
            )


from celery import shared_task


@shared_task(queue="high_priority")
def _send_telegram_message(telegram_user_id: str, message: str, notification_id: str):
    """Send a plain Telegram message and update notification status."""
    from apps.notifications.models import Notification

    try:
        from apps.integrations.telegram.sender import send_message
        result = send_message(chat_id=telegram_user_id, text=message, parse_mode="Markdown")
        Notification.objects.filter(id=notification_id).update(
            status=Notification.Status.SENT,
            sent_at=timezone.now(),
            external_message_id=str(result.get("message_id", "")),
        )
    except Exception as e:
        logger.error("Telegram send failed for user %s: %s", telegram_user_id, e)
        Notification.objects.filter(id=notification_id).update(
            status=Notification.Status.FAILED,
            error_message=str(e),
        )


@shared_task(queue="high_priority")
def _send_telegram_approval(telegram_user_id: str, approval_id: str, notification_id: str):
    """Send a Telegram message with inline approve/reject buttons."""
    from apps.notifications.models import Notification
    from apps.approvals.models import ApprovalRequest

    try:
        approval = ApprovalRequest.objects.select_related("company").get(id=approval_id)
        from apps.integrations.telegram.sender import send_approval_message
        result = send_approval_message(
            chat_id=telegram_user_id,
            approval=approval,
        )
        msg_id = str(result.get("message_id", ""))
        ApprovalRequest.objects.filter(id=approval_id).update(
            telegram_message_id=msg_id,
            telegram_chat_id=telegram_user_id,
        )
        Notification.objects.filter(id=notification_id).update(
            status=Notification.Status.SENT,
            sent_at=timezone.now(),
            external_message_id=msg_id,
        )
    except Exception as e:
        logger.error("Telegram approval send failed: %s", e)
        Notification.objects.filter(id=notification_id).update(
            status=Notification.Status.FAILED,
            error_message=str(e),
        )
