"""
Notifications — Multi-channel notification delivery tracking.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.tenants.models import TenantManager

User = get_user_model()


class Notification(models.Model):

    class Channel(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        EMAIL = "email", "Email"
        IN_APP = "in_app", "In-App"

    class Priority(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        READ = "read", "Read"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "tenants.Company", on_delete=models.CASCADE, related_name="notifications"
    )
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    title = models.CharField(max_length=255)
    body = models.TextField()
    action_url = models.CharField(max_length=500, blank=True)

    # Reference to the object that triggered this notification
    ref_type = models.CharField(max_length=50, blank=True)
    ref_id = models.CharField(max_length=100, blank=True)

    # Delivery metadata
    external_message_id = models.CharField(max_length=200, blank=True)
    error_message = models.TextField(blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "recipient", "status"]),
        ]

    def __str__(self):
        return f"[{self.channel}] {self.title} → {self.recipient}"
