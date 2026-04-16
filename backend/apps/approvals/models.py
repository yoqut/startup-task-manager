"""
Approvals — Human-in-the-loop approval queue.
Every agent action above the autonomy threshold lands here before execution.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.tenants.models import TenantManager
from apps.agents.models import AgentType

User = get_user_model()


class ApprovalRequest(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        AUTO_APPROVED = "auto_approved", "Auto-Approved"

    class ActionCategory(models.TextChoices):
        TASK_MANAGEMENT = "task_management", "Task Management"
        COMMUNICATION = "communication", "Communication"
        DATA_CHANGE = "data_change", "Data Change"
        EXTERNAL_ACTION = "external_action", "External Action"
        REPORT_GENERATION = "report_generation", "Report Generation"
        WORKFLOW_EXECUTION = "workflow_execution", "Workflow Execution"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "tenants.Company", on_delete=models.CASCADE, related_name="approval_requests"
    )

    # Which agent created this request
    agent_type = models.CharField(max_length=50, choices=AgentType.choices)
    execution_log = models.OneToOneField(
        "agents.AgentExecutionLog",
        on_delete=models.CASCADE,
        related_name="approval_request",
        null=True,
        blank=True,
    )

    # What the agent wants to do
    action_category = models.CharField(max_length=50, choices=ActionCategory.choices)
    action_type = models.CharField(max_length=100)
    action_payload = models.JSONField(
        help_text="The exact data that will be used to execute the action upon approval."
    )

    # Human-readable explanation
    title = models.CharField(max_length=500)
    reasoning = models.TextField(help_text="AI's explanation of why this action is recommended.")
    confidence_score = models.FloatField()

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    decided_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approval_decisions"
    )
    decision_comment = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    # Expiry — auto-rejected if not decided before this
    expires_at = models.DateTimeField()

    # Telegram tracking (for inline button approvals)
    telegram_message_id = models.CharField(max_length=100, blank=True)
    telegram_chat_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        verbose_name = "Approval Request"
        verbose_name_plural = "Approval Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "expires_at"]),
        ]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expires_at < timezone.now() and self.status == self.Status.PENDING
