import os
from django.db import models
from django.utils import timezone


class ReportStatus(models.TextChoices):
    SUBMITTED = "submitted", "Yuborildi"
    ACCEPTED = "accepted", "Qabul qilindi"
    REJECTED = "rejected", "Rad etildi"


class FileType(models.TextChoices):
    FILE = "file", "Fayl"
    IMAGE = "image", "Rasm"
    VIDEO = "video", "Video"


def report_upload_path(instance, filename):
    now = timezone.now()
    return os.path.join(
        "reports",
        str(instance.report.task_id),
        str(instance.report.employee_id),
        str(now.year),
        str(now.month),
        filename,
    )


class Report(models.Model):
    task = models.ForeignKey(
        "tasks.TaskInstance",
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name="Vazifa",
    )
    employee = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="submitted_reports",
        verbose_name="Xodim",
    )
    text = models.TextField(blank=True, null=True, verbose_name="Matn")
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.SUBMITTED,
        db_index=True,
        verbose_name="Holat",
    )
    manager_comment = models.TextField(
        blank=True,
        null=True,
        verbose_name="Menejer izohi",
    )
    submitted_at = models.DateTimeField(default=timezone.now, verbose_name="Yuborilgan vaqt")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Ko'rib chiqilgan vaqt")
    reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_reports",
        verbose_name="Ko'rib chiqqan",
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Hisobot"
        verbose_name_plural = "Hisobotlar"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["task", "employee"]),
            models.Index(fields=["status"]),
            models.Index(fields=["submitted_at"]),
        ]

    def __str__(self):
        return f"Hisobot: {self.task.title} - {self.employee}"

    def accept(self, reviewer, comment=""):
        self.status = ReportStatus.ACCEPTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        if comment:
            self.manager_comment = comment
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "manager_comment", "updated_at"])

    def reject(self, reviewer, comment):
        self.status = ReportStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.manager_comment = comment
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "manager_comment", "updated_at"])


class ReportAttachment(models.Model):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Hisobot",
    )
    file = models.FileField(upload_to=report_upload_path, verbose_name="Fayl")
    file_type = models.CharField(
        max_length=10,
        choices=FileType.choices,
        verbose_name="Fayl turi",
    )
    original_name = models.CharField(max_length=255, verbose_name="Asl nomi")
    telegram_file_id = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="Telegram fayl ID",
    )
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name="Yuklangan vaqt")

    class Meta:
        verbose_name = "Hisobot ilovasi"
        verbose_name_plural = "Hisobot ilovalari"
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"{self.original_name} ({self.get_file_type_display()})"

    def get_file_size_mb(self):
        try:
            return round(self.file.size / (1024 * 1024), 2)
        except Exception:
            return 0
