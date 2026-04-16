from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Invitation


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "full_name", "company", "role", "is_active", "created_at"]
    list_filter = ["role", "is_active", "company__name"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "avatar")}),
        ("Company", {"fields": ("company", "role", "department")}),
        ("Telegram", {"fields": ("telegram_user_id", "telegram_username")}),
        ("Notifications", {"fields": ("notify_via_telegram", "notify_via_email")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "company", "role", "password1", "password2"),
        }),
    )


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "company", "role", "invited_by", "is_accepted", "expires_at"]
    list_filter = ["role", "is_accepted"]
    search_fields = ["email", "company__name"]
