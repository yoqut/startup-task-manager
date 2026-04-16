"""
Integrations views — Telegram webhook + CRM/ERP CRUD + incoming webhooks.
"""
import json
import logging
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdminOrAbove
from .models import ExternalIntegration, IntegrationSyncLog
from .serializers import ExternalIntegrationSerializer, IntegrationSyncLogSerializer

logger = logging.getLogger("apps.integrations")


# ── Telegram Webhook ──────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def telegram_webhook(request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if settings.TELEGRAM_WEBHOOK_SECRET and secret != settings.TELEGRAM_WEBHOOK_SECRET:
        logger.warning("Invalid Telegram webhook secret token received")
        return HttpResponse(status=403)
    try:
        update = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)
    from apps.integrations.tasks import process_telegram_update
    process_telegram_update.delay(update)
    return HttpResponse(status=200)


# ── CRM/ERP incoming webhook (unauthenticated, validated by secret) ───────────

@csrf_exempt
@require_POST
def crm_webhook(request, integration_id):
    """
    Receives data pushed from an external CRM/ERP.
    Validates the X-Webhook-Secret header, then processes asynchronously.
    """
    try:
        integration = ExternalIntegration.objects.get(id=integration_id, is_active=True)
    except ExternalIntegration.DoesNotExist:
        return HttpResponse(status=404)

    secret = request.headers.get("X-Webhook-Secret", "")
    if integration.webhook_secret and secret != integration.webhook_secret:
        logger.warning("Invalid webhook secret for integration %s", integration_id)
        return HttpResponse(status=403)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    from apps.integrations.tasks import process_crm_webhook
    process_crm_webhook.delay(str(integration.id), payload)
    return JsonResponse({"status": "received"})


# ── CRM/ERP REST ViewSet (authenticated, owner/admin only) ───────────────────

class ExternalIntegrationViewSet(viewsets.ModelViewSet):
    serializer_class   = ExternalIntegrationSerializer
    permission_classes = [IsAdminOrAbove]

    def get_queryset(self):
        return ExternalIntegration.objects.for_company(self.request.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.company)

    @action(detail=True, methods=["get"], url_path="logs")
    def logs(self, request, pk=None):
        integration = self.get_object()
        qs = integration.sync_logs.all()[:50]
        return Response(IntegrationSyncLogSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="test")
    def test_connection(self, request, pk=None):
        """Quick connectivity check — tries to reach the configured API URL."""
        integration = self.get_object()
        if not integration.api_url:
            return Response({"ok": False, "error": "No API URL configured."})
        try:
            import requests as req
            resp = req.get(
                integration.api_url.rstrip("/") + "/",
                headers={"Authorization": f"Bearer {integration.api_key}"},
                timeout=5,
            )
            return Response({"ok": resp.status_code < 500, "status_code": resp.status_code})
        except Exception as e:
            return Response({"ok": False, "error": str(e)})

    @action(detail=True, methods=["post"], url_path="sync")
    def manual_sync(self, request, pk=None):
        """Trigger a manual outbound sync — pushes all tasks with matching external_ref_type."""
        integration = self.get_object()
        if integration.sync_direction == "import":
            return Response({"error": "This integration is import-only."}, status=400)

        from apps.tasks.models import Task
        from apps.integrations.sync import push_task_to_crm

        tasks = Task.objects.for_company(request.company).filter(
            external_ref_type=integration.type,
        ).exclude(external_ref_id="")

        pushed = 0
        for task in tasks:
            if push_task_to_crm(integration, task):
                pushed += 1

        from django.utils import timezone
        integration.last_sync_at = timezone.now()
        integration.sync_count  += pushed
        integration.save(update_fields=["last_sync_at", "sync_count"])

        return Response({"pushed": pushed})
