from django.contrib import admin
from .models import NotificationLog, TelegramUpdateLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "notification_type",
        "is_sent",
        "sent_at",
        "created_at",
        "get_error_preview",
    )
    list_filter = ("notification_type", "is_sent", "created_at")
    search_fields = ("user__full_name", "user__username", "message")
    readonly_fields = ("user", "notification_type", "message", "is_sent", "sent_at", "error_message", "created_at")
    ordering = ("-created_at",)
    list_per_page = 50
    list_select_related = ("user",)
    date_hierarchy = "created_at"

    def get_error_preview(self, obj):
        if obj.error_message:
            return obj.error_message[:50] + "..." if len(obj.error_message) > 50 else obj.error_message
        return "—"
    get_error_preview.short_description = "Xato"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    actions = ["retry_failed"]

    def retry_failed(self, request, queryset):
        from celery_tasks.reminders import retry_failed_notifications
        failed = queryset.filter(is_sent=False)
        for notification in failed:
            retry_failed_notifications.delay(notification.id)
        self.message_user(request, f"{failed.count()} bildirishnoma qayta yuborish uchun navbatga qo'yildi.")
    retry_failed.short_description = "Muvaffaqiyatsiz bildirishnomalarni qayta yuborish"


@admin.register(TelegramUpdateLog)
class TelegramUpdateLogAdmin(admin.ModelAdmin):
    list_display = ("update_id", "processed_at")
    readonly_fields = ("update_id", "processed_at", "raw_json")
    ordering = ("-processed_at",)
    list_per_page = 100
    date_hierarchy = "processed_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
