import json
from django.db import models
from django.utils import timezone


class NotificationType(models.TextChoices):
    TASK_ASSIGNED = "task_assigned", "Vazifa tayinlandi"
    TASK_REMINDER = "task_reminder", "Vazifa eslatmasi"
    TASK_OVERDUE = "task_overdue", "Muddati o'tgan vazifa"
    TASK_STATUS_CHANGED = "task_status_changed", "Holat o'zgartirildi"
    REPORT_SUBMITTED = "report_submitted", "Hisobot yuborildi"
    REPORT_ACCEPTED = "report_accepted", "Hisobot qabul qilindi"
    REPORT_REJECTED = "report_rejected", "Hisobot rad etildi"
    REPORT_OVERDUE = "report_overdue", "Hisobot muddati o'tdi"
    RECURRING_TASK_CREATED = "recurring_task_created", "Takrorlanuvchi vazifa yaratildi"
    DEPARTMENT_SUMMARY = "department_summary", "Bo'lim xulosasi"


class NotificationLog(models.Model):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notification_logs",
        verbose_name="Foydalanuvchi",
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        db_index=True,
        verbose_name="Bildirishnoma turi",
    )
    message = models.TextField(verbose_name="Xabar")
    is_sent = models.BooleanField(default=False, db_index=True, verbose_name="Yuborildi")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Yuborilgan vaqt")
    error_message = models.TextField(blank=True, default="", verbose_name="Xato xabari")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan")

    class Meta:
        verbose_name = "Bildirishnoma logi"
        verbose_name_plural = "Bildirishnoma loglari"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_sent"]),
            models.Index(fields=["notification_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user} | {self.get_notification_type_display()} | {'✓' if self.is_sent else '✗'}"

    def mark_sent(self):
        self.is_sent = True
        self.sent_at = timezone.now()
        self.save(update_fields=["is_sent", "sent_at"])

    def mark_failed(self, error):
        self.is_sent = False
        self.error_message = str(error)[:500]
        self.save(update_fields=["is_sent", "error_message"])


class TelegramUpdateLog(models.Model):
    update_id = models.BigIntegerField(unique=True, db_index=True, verbose_name="Update ID")
    processed_at = models.DateTimeField(default=timezone.now, verbose_name="Qayta ishlangan")
    raw_json = models.TextField(blank=True, default="", verbose_name="Raw JSON")

    class Meta:
        verbose_name = "Telegram update logi"
        verbose_name_plural = "Telegram update loglari"
        ordering = ["-processed_at"]

    def __str__(self):
        return f"Update #{self.update_id}"

    def set_raw(self, data: dict):
        self.raw_json = json.dumps(data, ensure_ascii=False)[:5000]
