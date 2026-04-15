from django.contrib import admin
from django.utils.html import format_html
from .models import Report, ReportAttachment, ReportStatus


class ReportAttachmentInline(admin.TabularInline):
    model = ReportAttachment
    fields = ("original_name", "file_type", "file", "uploaded_at")
    readonly_fields = ("original_name", "file_type", "uploaded_at")
    extra = 0
    can_delete = False


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "get_task_title",
        "employee",
        "get_status_badge",
        "submitted_at",
        "reviewed_by",
        "reviewed_at",
        "get_attachments_count",
    )
    list_filter = ("status", "submitted_at")
    search_fields = ("task__title", "employee__full_name", "text")
    readonly_fields = ("submitted_at", "created_at", "updated_at")
    list_select_related = ("task", "employee", "reviewed_by")
    ordering = ("-submitted_at",)
    list_per_page = 30
    inlines = [ReportAttachmentInline]
    date_hierarchy = "submitted_at"

    fieldsets = (
        (
            "Hisobot ma'lumotlari",
            {"fields": ("task", "employee", "text")},
        ),
        (
            "Ko'rib chiqish",
            {"fields": ("status", "manager_comment", "reviewed_by", "reviewed_at")},
        ),
        (
            "Meta",
            {"fields": ("submitted_at", "created_at", "updated_at")},
        ),
    )

    def get_task_title(self, obj):
        return obj.task.title[:50]
    get_task_title.short_description = "Vazifa"

    def get_status_badge(self, obj):
        colors = {
            ReportStatus.SUBMITTED: "blue",
            ReportStatus.ACCEPTED: "green",
            ReportStatus.REJECTED: "red",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )
    get_status_badge.short_description = "Holat"

    def get_attachments_count(self, obj):
        return obj.attachments.count()
    get_attachments_count.short_description = "Ilovalar"

    actions = ["accept_reports", "reject_reports"]

    def accept_reports(self, request, queryset):
        from django.utils import timezone
        queryset.update(
            status=ReportStatus.ACCEPTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"{queryset.count()} hisobot qabul qilindi.")
    accept_reports.short_description = "Hisobotlarni qabul qilish"

    def reject_reports(self, request, queryset):
        from django.utils import timezone
        queryset.update(
            status=ReportStatus.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
            manager_comment="Admin tomonidan rad etildi",
        )
        self.message_user(request, f"{queryset.count()} hisobot rad etildi.")
    reject_reports.short_description = "Hisobotlarni rad etish"


@admin.register(ReportAttachment)
class ReportAttachmentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "file_type", "report", "uploaded_at")
    list_filter = ("file_type",)
    search_fields = ("original_name", "report__task__title")
    readonly_fields = ("uploaded_at",)
    list_select_related = ("report__task", "report__employee")
    ordering = ("-uploaded_at",)
    list_per_page = 50
