"""
Chat — WebSocket-based chat rooms with company/branch/department/direct scopes.
"""
import uuid
from django.conf import settings
from django.db import models
from apps.tenants.models import TenantManager


class ChatRoom(models.Model):
    class Type(models.TextChoices):
        COMPANY    = "company",    "Company-wide"
        BRANCH     = "branch",     "Branch / multiple branches"
        DEPARTMENT = "department", "Department / multiple departments"
        DIRECT     = "direct",     "Direct (specific employees)"

    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "tenants.Company", on_delete=models.CASCADE, related_name="chat_rooms"
    )
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    type        = models.CharField(max_length=20, choices=Type.choices, default=Type.COMPANY)

    # For BRANCH / DEPARTMENT type — which org units are included
    org_units = models.ManyToManyField(
        "organizations.Department",
        blank=True,
        related_name="chat_rooms",
    )

    # For DIRECT type — explicit participant list
    # Also used for BRANCH/DEPT to add extra members beyond org unit membership
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="chat_rooms",
    )

    # Optional context links (discussions about a task or report)
    related_task   = models.ForeignKey(
        "tasks.Task",    null=True, blank=True,
        on_delete=models.SET_NULL, related_name="chat_rooms",
    )
    related_report = models.ForeignKey(
        "reports.Report", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="chat_rooms",
    )

    # Optional Telegram bridge — if set, messages are forwarded to/from this Telegram chat
    telegram_chat_id = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Telegram group/channel chat ID to bridge with this room (e.g. -100123456789)",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name="created_chat_rooms",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)   # bumped on new message

    objects = TenantManager()

    class Meta:
        verbose_name        = "Chat Room"
        verbose_name_plural = "Chat Rooms"
        ordering            = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    def can_access(self, user):
        """Returns True if the user is allowed to read/send in this room."""
        if user.company_id != self.company_id:
            return False
        if self.type == self.Type.COMPANY:
            return True
        if self.type in (self.Type.BRANCH, self.Type.DEPARTMENT):
            # User's dept is in org_units, OR explicitly added to members
            if user.dept_id and self.org_units.filter(pk=user.dept_id).exists():
                return True
            return self.members.filter(pk=user.pk).exists()
        if self.type == self.Type.DIRECT:
            return self.members.filter(pk=user.pk).exists()
        return False


class ChatMessage(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room       = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    author     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name="chat_messages",
    )
    body                = models.TextField()
    # Fallback display name for messages from unlinked Telegram users
    author_display_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at  = models.DateTimeField(null=True, blank=True)

    # Optional links so a message can reference a task or report
    related_task   = models.ForeignKey(
        "tasks.Task",    null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    related_report = models.ForeignKey(
        "reports.Report", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        verbose_name        = "Chat Message"
        verbose_name_plural = "Chat Messages"
        ordering            = ["created_at"]

    def __str__(self):
        return f"{self.author} @ {self.room}: {self.body[:40]}"
