from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "industry", "plan", "employee_count", "agent_autonomy_level", "is_active", "created_at"]
    list_filter = ["plan", "industry", "is_active"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "slug", "tokens_used_today", "tokens_reset_at", "created_at", "updated_at"]
