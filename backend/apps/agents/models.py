"""
Agents — Agent configuration, execution log, and prompt management.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.tenants.models import TenantManager

User = get_user_model()


class AgentType(models.TextChoices):
    COORDINATOR = "coordinator", "Coordinator Agent"
    OPERATIONS = "operations", "Operations Agent"
    CUSTOMER_SUPPORT = "customer_support", "Customer Support Agent"
    SALES = "sales", "Sales Agent"
    MARKETING = "marketing", "Marketing Agent"
    ANALYTICS = "analytics", "Analytics Agent"


class AgentConfiguration(models.Model):
    """
    Per-company configuration for each agent type.
    Controls autonomy, enabled state, system prompt, parent agent, and token budgets.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "tenants.Company", on_delete=models.CASCADE, related_name="agent_configs"
    )
    agent_type = models.CharField(max_length=50, choices=AgentType.choices)

    is_enabled = models.BooleanField(default=True)

    # Autonomy: 0.0 = every action needs approval, 1.0 = fully autonomous
    autonomy_level = models.FloatField(default=0.3)

    # System prompt for this agent (overrides code-level default when set)
    system_prompt = models.TextField(
        blank=True,
        help_text="Full system prompt for this agent. Leave blank to use the platform default.",
    )

    # Additional company-specific instructions appended to the system prompt
    custom_instructions = models.TextField(
        blank=True,
        help_text="Extra instructions specific to your company, appended after the system prompt.",
    )

    # Parent agent — which agent supervises / delegates to this one
    # e.g. Operations, Sales, Support all report to Coordinator
    parent_agent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_agents",
        help_text="The supervising agent that can delegate tasks to this agent. None = top-level.",
    )

    # Departments this agent is responsible for (empty = all departments)
    departments = models.ManyToManyField(
        "organizations.Department",
        blank=True,
        related_name="agents",
        help_text="Departments this agent monitors. Empty = monitors all departments.",
    )

    # Chat monitoring — if True, agent scans messages in linked department rooms
    monitor_chats = models.BooleanField(
        default=False,
        help_text="If enabled, agent analyzes chat messages in linked department rooms.",
    )

    # Per-agent daily token budget (falls back to company-level if null)
    daily_token_budget = models.PositiveIntegerField(null=True, blank=True)

    # Schedule config (for scheduled agents like Analytics)
    schedule_config = models.JSONField(
        default=dict,
        help_text='e.g., {"daily_briefing_hour": 8, "timezone": "Asia/Tashkent"}',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        unique_together = ("company", "agent_type")
        verbose_name = "Agent Configuration"

    def __str__(self):
        return f"{self.get_agent_type_display()} config for {self.company.name}"

    def get_effective_system_prompt(self) -> str:
        """
        Returns the system prompt to use for this agent:
        1. DB-stored system_prompt (if set by admin/user)
        2. Falls back to the hardcoded default in prompts.py
        """
        if self.system_prompt.strip():
            return self.system_prompt
        from apps.agents.engine.prompts import AGENT_PROMPTS
        return AGENT_PROMPTS.get(self.agent_type, "")


class AgentExecutionLog(models.Model):
    """
    Immutable record of every agent execution.
    Captures input context, LLM output, actions taken, and outcome.
    Used for audit, debugging, and training autonomy calibration.
    """

    class Status(models.TextChoices):
        STARTED = "started", "Started"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class TriggerSource(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled (Celery Beat)"
        USER_COMMAND = "user_command", "User Command"
        TELEGRAM = "telegram", "Telegram Command"
        WORKFLOW = "workflow", "Workflow Trigger"
        SYSTEM_EVENT = "system_event", "System Event"
        AGENT_DELEGATION = "agent_delegation", "Agent Delegation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "tenants.Company", on_delete=models.CASCADE, related_name="agent_logs"
    )
    agent_type = models.CharField(max_length=50, choices=AgentType.choices)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.STARTED)
    trigger_source = models.CharField(max_length=30, choices=TriggerSource.choices)
    triggered_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    # What the agent was asked to do
    task_description = models.TextField()

    # Structured context sent to the LLM (the prompt payload)
    input_context = models.JSONField(default=dict)

    # Raw LLM response
    llm_response = models.TextField(blank=True)

    # Parsed structured output from the LLM
    parsed_output = models.JSONField(default=dict)

    # Actions the agent took or proposed
    actions_taken = models.JSONField(default=list)

    # AI self-reported confidence (0.0 → 1.0)
    confidence_score = models.FloatField(null=True, blank=True)

    # Token usage
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    # Error info
    error_message = models.TextField(blank=True)

    objects = TenantManager()

    class Meta:
        verbose_name = "Agent Execution Log"
        verbose_name_plural = "Agent Execution Logs"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["company", "agent_type", "status"]),
            models.Index(fields=["company", "started_at"]),
        ]

    def __str__(self):
        return f"{self.get_agent_type_display()} | {self.get_status_display()} | {self.started_at:%Y-%m-%d %H:%M}"


class AgentPromptTemplate(models.Model):
    """
    Versioned prompt templates for each agent type.
    Allows updating prompts without code deployments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_type = models.CharField(max_length=50, choices=AgentType.choices)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    system_prompt = models.TextField()
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("agent_type", "version")
        ordering = ["-version"]
        verbose_name = "Agent Prompt Template"

    def __str__(self):
        return f"{self.get_agent_type_display()} v{self.version}"
