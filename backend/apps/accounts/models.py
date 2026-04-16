"""
Accounts — Custom User model with Role-Based Access Control.
Users always belong to exactly one Company (tenant).
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.OWNER)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user. Email is the unique identifier (not username).
    Each user belongs to one Company (the tenant).
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Core identity
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    # Tenant relationship
    company = models.ForeignKey(
        "tenants.Company",
        on_delete=models.CASCADE,
        related_name="members",
        null=True,  # null during registration before company is assigned
        blank=True,
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    department = models.CharField(max_length=100, blank=True)  # legacy free-text field kept for compatibility
    dept = models.ForeignKey(
        "organizations.Department",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )

    # Telegram
    telegram_user_id = models.CharField(max_length=100, blank=True, unique=True, null=True)
    telegram_username = models.CharField(max_length=100, blank=True)

    # Notification preferences
    notify_via_telegram = models.BooleanField(default=True)
    notify_via_email = models.BooleanField(default=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["first_name", "last_name"]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    # ── Permission helpers ───────────────────────────────────────────────────
    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_admin_or_above(self):
        return self.role in (self.Role.OWNER, self.Role.ADMIN)

    @property
    def is_manager_or_above(self):
        return self.role in (self.Role.OWNER, self.Role.ADMIN, self.Role.MANAGER)

    def can_approve_actions(self):
        return self.is_manager_or_above

    def can_configure_agents(self):
        return self.is_admin_or_above

    def can_manage_team(self):
        return self.is_admin_or_above


class Invitation(models.Model):
    """
    Pending invitation for a new team member.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "tenants.Company", on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=User.Role.choices, default=User.Role.MEMBER)
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="sent_invitations"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_accepted = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "email")

    def __str__(self):
        return f"Invitation for {self.email} to {self.company.name}"
