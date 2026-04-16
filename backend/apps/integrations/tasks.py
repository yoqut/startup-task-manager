"""
Integrations Celery tasks.
"""
from celery import shared_task
import logging

logger = logging.getLogger("apps.integrations")


@shared_task(queue="high_priority")
def process_telegram_update(update: dict):
    """Process a Telegram update in the background."""
    from apps.integrations.telegram.handlers import handle_update
    try:
        handle_update(update)
    except Exception as e:
        logger.exception("Failed to process Telegram update: %s", e)


@shared_task(queue="high_priority", bind=True, max_retries=2)
def process_crm_webhook(self, integration_id: str, payload: dict):
    """
    Process an incoming CRM/ERP webhook:
    translate payload → create/update AIManager task.
    """
    from apps.integrations.models import ExternalIntegration, IntegrationSyncLog
    from apps.integrations.sync import process_inbound_payload
    from django.utils import timezone

    try:
        integration = ExternalIntegration.objects.select_related("company").get(
            id=integration_id, is_active=True
        )
    except ExternalIntegration.DoesNotExist:
        return

    try:
        stats = process_inbound_payload(integration, payload)

        IntegrationSyncLog.objects.create(
            integration=integration,
            direction="inbound",
            result="success",
            payload=payload,
            response=stats,
            records_in=stats.get("created", 0) + stats.get("updated", 0),
        )
        integration.last_sync_at = timezone.now()
        integration.sync_count  += stats.get("created", 0) + stats.get("updated", 0)
        integration.last_error   = ""
        integration.save(update_fields=["last_sync_at", "sync_count", "last_error"])

        logger.info("CRM webhook processed | integration=%s | %s", integration_id, stats)

    except Exception as exc:
        logger.exception("CRM webhook processing failed | integration=%s", integration_id)
        IntegrationSyncLog.objects.create(
            integration=integration,
            direction="inbound",
            result="failed",
            payload=payload,
            error=str(exc),
        )
        integration.last_error = str(exc)
        integration.save(update_fields=["last_error"])
        raise self.retry(exc=exc, countdown=60)
