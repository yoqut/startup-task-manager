from django.db import models
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Nomi")
    description = models.TextField(blank=True, default="", verbose_name="Tavsif")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Faol")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Bo'lim"
        verbose_name_plural = "Bo'limlar"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name

    def get_head(self):
        from apps.users.models import UserRole
        return self.members.filter(role=UserRole.HEAD, is_active=True).first()

    def get_employees(self):
        from apps.users.models import UserRole
        return self.members.filter(role=UserRole.EMPLOYEE, is_active=True)

    def get_active_tasks_count(self):
        from apps.tasks.models import TaskStatus
        return self.task_instances.filter(
            status__in=[TaskStatus.NEW, TaskStatus.IN_PROGRESS]
        ).count()

    def get_completed_tasks_count(self):
        from apps.tasks.models import TaskStatus
        return self.task_instances.filter(status=TaskStatus.COMPLETED).count()

    def get_overdue_tasks_count(self):
        from apps.tasks.models import TaskStatus
        return self.task_instances.filter(status=TaskStatus.OVERDUE).count()
