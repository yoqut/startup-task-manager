from django.contrib import admin
from .models import Report, ReportComment


class ReportCommentInline(admin.TabularInline):
    model = ReportComment
    extra = 0
    readonly_fields = ["author", "created_at"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display  = ["title", "report_type", "sent_by", "sent_to", "department", "status", "created_at"]
    list_filter   = ["report_type", "status", "department"]
    search_fields = ["title", "body", "sent_by__email"]
    inlines       = [ReportCommentInline]
    readonly_fields = ["created_at", "updated_at"]
