from rest_framework import serializers
from .models import ApprovalRequest


class ApprovalRequestSerializer(serializers.ModelSerializer):
    agent_type_display = serializers.CharField(source="get_agent_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    decided_by_name = serializers.CharField(source="decided_by.full_name", read_only=True)
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = ApprovalRequest
        fields = [
            "id", "agent_type", "agent_type_display", "action_category",
            "action_type", "action_payload", "title", "reasoning",
            "confidence_score", "status", "status_display",
            "decided_by", "decided_by_name", "decision_comment",
            "decided_at", "expires_at", "is_expired", "created_at",
        ]
        read_only_fields = [
            "id", "agent_type", "action_category", "action_type",
            "action_payload", "title", "reasoning", "confidence_score",
            "decided_by", "decided_at", "expires_at", "is_expired", "created_at",
        ]
