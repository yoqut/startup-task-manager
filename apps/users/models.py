from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    BOSS = "boss", "Boshliq"
    HEAD = "head", "Bo'lim boshlig'i"
    EMPLOYEE = "employee", "Ishchi"


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")
        user = self.model(username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.BOSS)
        return self.create_user(username, password, **extra_fields)

    def get_by_telegram_id(self, telegram_id):
        return self.filter(telegram_id=telegram_id).first()


class User(AbstractBaseUser, PermissionsMixin):
    telegram_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Telegram ID",
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Foydalanuvchi nomi",
    )
    full_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="To'liq ism",
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="Telefon raqam",
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Rol",
    )
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        verbose_name="Bo'lim",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    is_staff = models.BooleanField(default=False, verbose_name="Admin xodim")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        indexes = [
            models.Index(fields=["telegram_id"]),
            models.Index(fields=["role"]),
            models.Index(fields=["department"]),
        ]

    def __str__(self):
        return self.full_name or self.username

    @property
    def is_boss(self):
        return self.role == UserRole.BOSS

    @property
    def is_head(self):
        return self.role == UserRole.HEAD

    @property
    def is_employee(self):
        return self.role == UserRole.EMPLOYEE

    @property
    def has_role(self):
        return self.role is not None

    def get_display_name(self):
        if self.full_name:
            return self.full_name
        return self.username
