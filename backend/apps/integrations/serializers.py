from rest_framework import serializers
from .models import ExternalIntegration, IntegrationSyncLog


class ExternalIntegrationSerializer(serializers.ModelSerializer):
    type_display           = serializers.CharField(source="get_type_display", read_only=True)
    sync_direction_display = serializers.CharField(source="get_sync_direction_display", read_only=True)
    webhook_url            = serializers.CharField(source="webhook_url_path", read_only=True)

    class Meta:
        model  = ExternalIntegration
        fields = [
            "id", "name", "type", "type_display",
            "sync_direction", "sync_direction_display",
            "api_url", "api_key", "webhook_secret", "webhook_url",
            "config", "is_active",
            "last_sync_at", "sync_count", "last_error",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "type_display", "sync_direction_display", "webhook_url",
            "last_sync_at", "sync_count", "last_error", "created_at", "updated_at",
        ]
        extra_kwargs = {
            "api_key":        {"write_only": False},   # show masked; full value for edit
            "webhook_secret": {"write_only": False},
        }


class IntegrationSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = IntegrationSyncLog
        fields = [
            "id", "direction", "result", "records_in", "records_out",
            "error", "created_at",
        ]
        read_only_fields = fields
