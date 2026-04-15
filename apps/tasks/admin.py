from django.contrib import admin
from django.utils.html import format_html
from .models import TaskTemplate, TaskInstance, TaskStatusHistory, TaskStatus, Priority


class TaskStatusHistoryInline(admin.TabularInline):
    model = TaskStatusHistory
    fields = ("old_status", "new_status", "changed_by", "comment", "created_at")
    readonly_fields = ("old_status", "new_status", "changed_by", "comment", "created_at")
    extra = 0
    can_delete = False
    ordering = ("-created_at",)


@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "creator",
        "assigned_department",
        "assigned_user",
        "priority",
        "task_type",
        "recurrence_type",
        "start_date",
        "is_active",
        "created_at",
    )
    list_filter = (
        "task_type",
        "recurrence_type",
        "priority",
        "is_active",
        "report_required",
        "report_frequency",
    )
    search_fields = ("title", "description", "creator__full_name", "creator__username")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("creator", "assigned_department", "assigned_user")
    ordering = ("-created_at",)
    list_per_page = 30

    fieldsets = (
        (
            "Asosiy ma'lumotlar",
            {"fields": ("title", "description", "instructions", "priority")},
        ),
        (
            "Tayinlash",
            {"fields": ("creator", "assigned_department", "assigned_user")},
        ),
        (
            "Vazifa turi va takrorlanish",
            {
                "fields": (
                    "task_type",
                    "recurrence_type",
                    "start_date",
                    "end_date",
                    "estimated_duration",
                )
            },
        ),
        (
            "Hisobot sozlamalari",
            {
                "fields": (
                    "report_required",
                    "report_frequency",
                    "attachments_allowed",
                )
            },
        ),
        (
            "Holat",
            {"fields": ("is_active", "created_at", "updated_at")},
        ),
    )

    actions = ["activate_templates", "deactivate_templates"]

    def activate_templates(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} shablon faollashtirildi.")
    activate_templates.short_description = "Shablonlarni faollashtirish"

    def deactivate_templates(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} shablon o'chirildi.")
    deactivate_templates.short_description = "Shablonlarni o'chirish"


@admin.register(TaskInstance)
class TaskInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "creator",
        "assigned_user",
        "assigned_department",
        "get_priority_badge",
        "get_status_badge",
        "due_at",
        "is_overdue",
        "created_at",
    )
    list_filter = (
        "status",
        "priority",
        "is_overdue",
        "report_required",
        "report_frequency",
        "assigned_department",
    )
    search_fields = (
        "title",
        "description",
        "creator__full_name",
        "assigned_user__full_name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "completed_at",
        "is_overdue",
    )
    list_select_related = ("creator", "assigned_user", "assigned_department", "template")
    ordering = ("-created_at",)
    list_per_page = 30
    inlines = [TaskStatusHistoryInline]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Asosiy ma'lumotlar",
            {"fields": ("title", "description", "instructions", "priority", "template")},
        ),
        (
            "Tayinlash",
            {"fields": ("creator", "assigned_department", "assigned_user")},
        ),
        (
            "Holat va vaqt",
            {
                "fields": (
                    "status",
                    "due_at",
                    "start_at",
                    "completed_at",
                    "is_overdue",
                )
            },
        ),
        (
            "Hisobot sozlamalari",
            {
                "fields": (
                    "report_required",
                    "report_frequency",
                    "attachments_allowed",
                    "current_period_start",
                    "current_period_end",
                )
            },
        ),
        (
            "Meta",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    def get_priority_badge(self, obj):
        colors = {
            Priority.LOW: "gray",
            Priority.MEDIUM: "blue",
            Priority.HIGH: "orange",
            Priority.URGENT: "red",
        }
        color = colors.get(obj.priority, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display(),
        )
    get_priority_badge.short_description = "Ustuvorlik"

    def get_status_badge(self, obj):
        colors = {
            TaskStatus.NEW: "blue",
            TaskStatus.IN_PROGRESS: "orange",
            TaskStatus.COMPLETED: "green",
            TaskStatus.BLOCKED: "red",
            TaskStatus.CANCELLED: "gray",
            TaskStatus.OVERDUE: "darkred",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )
    get_status_badge.short_description = "Holat"

    actions = ["mark_completed", "mark_cancelled"]

    def mark_completed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status=TaskStatus.COMPLETED, completed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} vazifa bajarildi deb belgilandi.")
    mark_completed.short_description = "Bajarildi deb belgilash"

    def mark_cancelled(self, request, queryset):
        queryset.update(status=TaskStatus.CANCELLED)
        self.message_user(request, f"{queryset.count()} vazifa bekor qilindi.")
    mark_cancelled.short_description = "Bekor qilish"


@admin.register(TaskStatusHistory)
class TaskStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("task", "changed_by", "old_status", "new_status", "created_at")
    list_filter = ("old_status", "new_status")
    search_fields = ("task__title", "changed_by__full_name", "comment")
    readonly_fields = ("task", "changed_by", "old_status", "new_status", "comment", "created_at")
    ordering = ("-created_at",)
    list_per_page = 50
    list_select_related = ("task", "changed_by")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
