"""
Reports — Employee → Manager → Owner reporting chain.
Supports daily/weekly reports, issue escalations, and progress updates.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.tenants.models import TenantManager

User = get_user_model()


class Report(models.Model):

    class ReportType(models.TextChoices):
        DAILY    = "daily",    "Daily Report"
        WEEKLY   = "weekly",   "Weekly Report"
        ISSUE    = "issue",    "Issue / Problem"
        PROGRESS = "progress", "Progress Update"
        REQUEST  = "request",  "Request"

    class Status(models.TextChoices):
        SENT         = "sent",         "Sent"
        READ         = "read",         "Read"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "tenants.Company", on_delete=models.CASCADE, related_name="reports"
    )
    title       = models.CharField(max_length=255)
    body        = models.TextField()
    report_type = models.CharField(max_length=20, choices=ReportType.choices, default=ReportType.DAILY)
    department  = models.CharField(max_length=100, blank=True)
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT)

    sent_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_reports"
    )
    # null → sent to all managers/owners of the company
    sent_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="received_reports"
    )
    related_task = models.ForeignKey(
        "tasks.Task", on_delete=models.SET_NULL, null=True, blank=True, related_name="reports"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        verbose_name = "Report"
        verbose_name_plural = "Reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "sent_by"]),
            models.Index(fields=["company", "sent_to"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()}) by {self.sent_by}"


class ReportComment(models.Model):
    """Manager/owner replies to a report."""
    id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    body   = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on '{self.report.title}' by {self.author}"
