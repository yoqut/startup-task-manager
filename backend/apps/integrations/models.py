"""
External Integrations — CRM/ERP bridge.
Allows AIManager to sync tasks and data with third-party systems like
Bitrix24, AmoCRM, Odoo, 1C:Enterprise, or any generic webhook-based system.
"""
import uuid
from django.db import models
from apps.tenants.models import TenantManager


class ExternalIntegration(models.Model):

    class Type(models.TextChoices):
        BITRIX24 = "bitrix24", "Bitrix24"
        AMO_CRM  = "amocrm",   "AmoCRM"
        ODOO     = "odoo",     "Odoo ERP"
        ONE_C    = "1c",       "1C:Enterprise"
        GENERIC  = "generic",  "Generic Webhook"

    class SyncDirection(models.TextChoices):
        IMPORT = "import", "Import only (CRM → AIManager)"
        EXPORT = "export", "Export only (AIManager → CRM)"
        BOTH   = "both",   "Bidirectional"

    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "tenants.Company", on_delete=models.CASCADE, related_name="integrations"
    )
    name            = models.CharField(max_length=255)
    type            = models.CharField(max_length=20, choices=Type.choices, default=Type.GENERIC)
    sync_direction  = models.CharField(max_length=10, choices=SyncDirection.choices, default=SyncDirection.BOTH)

    # Connection details
    api_url         = models.CharField(max_length=500, blank=True, help_text="Base API URL of the CRM/ERP")
    api_key         = models.CharField(max_length=500, blank=True, help_text="API key or token")
    webhook_secret  = models.CharField(max_length=255, blank=True, help_text="Secret to validate incoming webhooks")

    # Type-specific settings (field mappings, filters, etc.)
    config = models.JSONField(
        default=dict,
        help_text=(
            "Type-specific configuration. Examples:\n"
            "Bitrix24: {\"portal_url\": \"...\", \"user_id\": ...}\n"
            "Odoo:     {\"db\": \"mydb\", \"uid\": 1}\n"
            "Generic:  {\"task_create_endpoint\": \"/tasks\", \"task_update_endpoint\": \"/tasks/{id}\"}"
        ),
    )

    is_active    = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_count   = models.PositiveIntegerField(default=0)
    last_error   = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        verbose_name        = "External Integration"
        verbose_name_plural = "External Integrations"
        ordering            = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()}) — {self.company.name}"

    @property
    def webhook_url_path(self):
        """The URL path for this integration's incoming webhook."""
        return f"/api/v1/integrations/crm/{self.id}/webhook/"


class IntegrationSyncLog(models.Model):
    """Records every sync event for auditing and debugging."""

    class Direction(models.TextChoices):
        INBOUND  = "inbound",  "Inbound (CRM → AIManager)"
        OUTBOUND = "outbound", "Outbound (AIManager → CRM)"

    class Result(models.TextChoices):
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial"
        FAILED  = "failed",  "Failed"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(
        ExternalIntegration, on_delete=models.CASCADE, related_name="sync_logs"
    )
    direction   = models.CharField(max_length=10, choices=Direction.choices)
    result      = models.CharField(max_length=10, choices=Result.choices, default=Result.SUCCESS)
    payload     = models.JSONField(default=dict)
    response    = models.JSONField(default=dict)
    records_in  = models.PositiveIntegerField(default=0, help_text="Records received / processed")
    records_out = models.PositiveIntegerField(default=0, help_text="Records pushed to external system")
    error       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Integration Sync Log"
