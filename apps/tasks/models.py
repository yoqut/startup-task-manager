from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class Priority(models.TextChoices):
    LOW = "low", "Past"
    MEDIUM = "medium", "O'rta"
    HIGH = "high", "Yuqori"
    URGENT = "urgent", "Shoshilinch"


class TaskType(models.TextChoices):
    ONE_TIME = "one_time", "Bir martalik"
    RECURRING = "recurring", "Takrorlanuvchi"


class RecurrenceType(models.TextChoices):
    NONE = "none", "Yo'q"
    DAILY = "daily", "Har kuni"
    WEEKLY = "weekly", "Har hafta"
    MONTHLY = "monthly", "Har oy"
    YEARLY = "yearly", "Har yil"


class ReportFrequency(models.TextChoices):
    NONE = "none", "Yo'q"
    DAILY = "daily", "Kunlik"
    WEEKLY = "weekly", "Haftalik"
    MONTHLY = "monthly", "Oylik"
    YEARLY = "yearly", "Yillik"


class TaskStatus(models.TextChoices):
    NEW = "new", "Yangi"
    IN_PROGRESS = "in_progress", "Jarayonda"
    COMPLETED = "completed", "Bajarildi"
    BLOCKED = "blocked", "Bloklangan"
    CANCELLED = "cancelled", "Bekor qilindi"
    OVERDUE = "overdue", "Muddati o'tgan"


class TaskTemplate(models.Model):
    creator = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="created_templates",
        verbose_name="Yaratuvchi",
    )
    assigned_department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_templates",
        verbose_name="Bo'lim",
    )
    assigned_user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_templates",
        verbose_name="Xodim",
    )
    title = models.CharField(max_length=500, verbose_name="Sarlavha")
    description = models.TextField(verbose_name="Tavsif")
    instructions = models.TextField(verbose_name="Ko'rsatmalar")
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="Ustuvorlik",
    )
    task_type = models.CharField(
        max_length=20,
        choices=TaskType.choices,
        default=TaskType.ONE_TIME,
        verbose_name="Vazifa turi",
    )
    recurrence_type = models.CharField(
        max_length=20,
        choices=RecurrenceType.choices,
        default=RecurrenceType.NONE,
        verbose_name="Takrorlanish turi",
    )
    report_frequency = models.CharField(
        max_length=20,
        choices=ReportFrequency.choices,
        default=ReportFrequency.NONE,
        verbose_name="Hisobot chastotasi",
    )
    start_date = models.DateField(verbose_name="Boshlanish sanasi")
    end_date = models.DateField(null=True, blank=True, verbose_name="Tugash sanasi")
    estimated_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Soatlarda",
        verbose_name="Taxminiy davomiyligi",
    )
    attachments_allowed = models.BooleanField(
        default=True,
        verbose_name="Ilova yuklashga ruxsat",
    )
    report_required = models.BooleanField(
        default=True,
        verbose_name="Hisobot majburiy",
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Faol")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Vazifa shabloni"
        verbose_name_plural = "Vazifa shablonlari"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task_type", "is_active"]),
            models.Index(fields=["recurrence_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_task_type_display()})"

    def clean(self):
        if not self.assigned_department and not self.assigned_user:
            raise ValidationError(
                "Bo'lim yoki xodim ko'rsatilishi kerak."
            )
        if self.task_type == TaskType.RECURRING and self.recurrence_type == RecurrenceType.NONE:
            raise ValidationError(
                "Takrorlanuvchi vazifa uchun takrorlanish turi ko'rsatilishi kerak."
            )


class TaskInstance(models.Model):
    template = models.ForeignKey(
        TaskTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instances",
        verbose_name="Shablon",
    )
    creator = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="created_task_instances",
        verbose_name="Yaratuvchi",
    )
    assigned_department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_instances",
        verbose_name="Bo'lim",
    )
    assigned_user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_task_instances",
        verbose_name="Xodim",
    )
    title = models.CharField(max_length=500, verbose_name="Sarlavha")
    description = models.TextField(verbose_name="Tavsif")
    instructions = models.TextField(verbose_name="Ko'rsatmalar")
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
        verbose_name="Ustuvorlik",
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.NEW,
        db_index=True,
        verbose_name="Holat",
    )
    due_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="Tugash vaqti")
    start_at = models.DateTimeField(null=True, blank=True, verbose_name="Boshlanish vaqti")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Bajarilish vaqti")
    is_overdue = models.BooleanField(default=False, db_index=True, verbose_name="Muddati o'tgan")
    report_required = models.BooleanField(default=True, verbose_name="Hisobot majburiy")
    report_frequency = models.CharField(
        max_length=20,
        choices=ReportFrequency.choices,
        default=ReportFrequency.NONE,
        verbose_name="Hisobot chastotasi",
    )
    attachments_allowed = models.BooleanField(default=True, verbose_name="Ilova yuklashga ruxsat")
    current_period_start = models.DateTimeField(null=True, blank=True, verbose_name="Joriy davr boshi")
    current_period_end = models.DateTimeField(null=True, blank=True, verbose_name="Joriy davr oxiri")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Vazifa"
        verbose_name_plural = "Vazifalar"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "is_overdue"]),
            models.Index(fields=["assigned_user", "status"]),
            models.Index(fields=["assigned_department", "status"]),
            models.Index(fields=["due_at", "status"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"

    def clean(self):
        if not self.assigned_department and not self.assigned_user:
            raise ValidationError("Bo'lim yoki xodim ko'rsatilishi kerak.")

    def mark_overdue(self):
        if (
            self.due_at
            and timezone.now() > self.due_at
            and self.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
        ):
            self.is_overdue = True
            if self.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                self.status = TaskStatus.OVERDUE
            self.save(update_fields=["is_overdue", "status", "updated_at"])
            return True
        return False

    def get_latest_report(self):
        return self.reports.order_by("-submitted_at").first()


class TaskStatusHistory(models.Model):
    task = models.ForeignKey(
        TaskInstance,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name="Vazifa",
    )
    changed_by = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="status_changes",
        verbose_name="O'zgartirgan",
    )
    old_status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        verbose_name="Eski holat",
    )
    new_status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        verbose_name="Yangi holat",
    )
    comment = models.TextField(blank=True, default="", verbose_name="Izoh")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan")

    class Meta:
        verbose_name = "Holat tarixi"
        verbose_name_plural = "Holat tarixlari"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task", "created_at"]),
        ]

    def __str__(self):
        return f"{self.task} | {self.old_status} → {self.new_status}"
