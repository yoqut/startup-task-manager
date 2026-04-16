from rest_framework import serializers
from .models import Company


class CompanySerializer(serializers.ModelSerializer):
    token_budget_remaining = serializers.ReadOnlyField()

    class Meta:
        model = Company
        fields = [
            "id", "name", "slug", "industry", "plan", "logo", "website",
            "employee_count", "timezone", "agent_autonomy_level",
            "daily_token_budget", "tokens_used_today", "token_budget_remaining",
            "telegram_chat_id", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "plan", "tokens_used_today",
            "token_budget_remaining", "created_at", "updated_at",
        ]
