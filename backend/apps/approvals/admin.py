from django.contrib import admin
from .models import ApprovalRequest


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "agent_type", "status", "confidence_score", "decided_by", "created_at", "expires_at"]
    list_filter = ["status", "agent_type", "action_category"]
    search_fields = ["title", "company__name"]
    readonly_fields = ["id", "created_at", "action_payload"]
