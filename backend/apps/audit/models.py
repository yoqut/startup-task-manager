"""
Audit — Immutable audit log for all significant system actions.
Append-only: records are never updated or deleted.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AuditLog(models.Model):

    class Actor(models.TextChoices):
        USER = "user", "Human User"
        AGENT = "agent", "AI Agent"
        SYSTEM = "system", "System"
        TELEGRAM = "telegram", "Telegram Bot"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "tenants.Company", on_delete=models.CASCADE, related_name="audit_logs"
    )

    # Who did it
    actor_type = models.CharField(max_length=20, choices=Actor.choices)
    actor_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    actor_agent = models.CharField(max_length=50, blank=True)

    # What happened
    action = models.CharField(
        max_length=100,
        help_text="Verb-noun format: e.g., task.created, approval.approved, agent.executed",
    )
    description = models.TextField()

    # What was affected
    target_type = models.CharField(max_length=50, blank=True)
    target_id = models.CharField(max_length=100, blank=True)

    # Full snapshot of the change
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict)

    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["company", "timestamp"]),
            models.Index(fields=["company", "action"]),
            models.Index(fields=["company", "actor_type"]),
        ]

    def __str__(self):
        return f"[{self.actor_type}] {self.action} @ {self.timestamp:%Y-%m-%d %H:%M:%S}"

    def save(self, *args, **kwargs):
        # Audit logs are immutable after creation
        if self.pk:
            raise ValueError("AuditLog records cannot be modified after creation.")
        super().save(*args, **kwargs)
