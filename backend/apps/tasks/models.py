"""
Tasks — Task management, workflows, and SLA tracking.
This is the primary data domain for the Operations Agent.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.tenants.models import TenantManager

User = get_user_model()


class Task(models.Model):

    class Status(models.TextChoices):
        BACKLOG = "backlog", "Backlog"
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        BLOCKED = "blocked", "Blocked"
        IN_REVIEW = "in_review", "In Review"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    class Department(models.TextChoices):
        OPERATIONS = "operations", "Operations"
        SALES = "sales", "Sales"
        MARKETING = "marketing", "Marketing"
        SUPPORT = "support", "Support"
        FINANCE = "finance", "Finance"
        HR = "hr", "HR"
        GENERAL = "general", "General"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "tenants.Company", on_delete=models.CASCADE, related_name="tasks"
    )
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    department = models.CharField(
        max_length=20, choices=Department.choices, default=Department.GENERAL
    )

    # People
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_tasks"
    )
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks"
    )

    # Hierarchy
    parent_task = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="subtasks"
    )

    # Time
    due_date = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    # AI metadata
    ai_priority_score = models.FloatField(null=True, blank=True)
    ai_suggested_assignee = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_suggested_tasks"
    )
    is_ai_created = models.BooleanField(default=False)
    blocker_reason = models.TextField(blank=True)

    # External reference (e.g., linked to a support ticket or lead)
    external_ref_type = models.CharField(max_length=50, blank=True)
    external_ref_id = models.CharField(max_length=100, blank=True)

    tags = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        ordering = ["-priority", "due_date", "-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "assigned_to"]),
            models.Index(fields=["company", "due_date"]),
        ]

    def __str__(self):
        return f"[{self.get_priority_display()}] {self.title}"

    @property
    def is_overdue(self):
        from django.utils import timezone
        return (
            self.due_date is not None
            and self.due_date < timezone.now()
            and self.status not in (self.Status.DONE, self.Status.CANCELLED)
        )

    @property
    def is_blocked(self):
        return self.status == self.Status.BLOCKED


class TaskComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    body = models.TextField()
    is_ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on {self.task.title} by {self.author}"


class Workflow(models.Model):
    """
    Automation rule: "When X happens, do Y."
    Evaluated by the Operations Agent continuously.
    """

    class TriggerType(models.TextChoices):
        TASK_CREATED = "task_created", "Task Created"
        TASK_STATUS_CHANGED = "task_status_changed", "Task Status Changed"
        TASK_OVERDUE = "task_overdue", "Task Overdue"
        TASK_BLOCKED = "task_blocked", "Task Blocked"
        TASK_UNASSIGNED = "task_unassigned", "Task Unassigned"
        DAILY_SCHEDULE = "daily_schedule", "Daily Schedule"
        WEEKLY_SCHEDULE = "weekly_schedule", "Weekly Schedule"

    class ActionType(models.TextChoices):
        NOTIFY_ASSIGNEE = "notify_assignee", "Notify Assignee"
        NOTIFY_MANAGER = "notify_manager", "Notify Manager"
        REASSIGN_TASK = "reassign_task", "Reassign Task"
        CREATE_SUBTASK = "create_subtask", "Create Subtask"
        ESCALATE_TO_AGENT = "escalate_to_agent", "Escalate to Agent"
        SEND_TELEGRAM = "send_telegram", "Send Telegram Message"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "tenants.Company", on_delete=models.CASCADE, related_name="workflows"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    trigger_type = models.CharField(max_length=50, choices=TriggerType.choices)
    trigger_conditions = models.JSONField(
        default=dict,
        help_text='e.g., {"department": "sales", "priority": "critical"}',
    )
    action_type = models.CharField(max_length=50, choices=ActionType.choices)
    action_config = models.JSONField(
        default=dict,
        help_text='e.g., {"message_template": "Task {title} is overdue!"}',
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    executions_count = models.PositiveIntegerField(default=0)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        verbose_name = "Workflow"
        verbose_name_plural = "Workflows"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_trigger_type_display()} → {self.get_action_type_display()})"
