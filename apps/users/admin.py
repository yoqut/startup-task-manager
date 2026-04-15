from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserRole


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "full_name",
        "telegram_id",
        "role",
        "department",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = ("role", "department", "is_active", "is_staff")
    search_fields = ("username", "full_name", "telegram_id", "phone_number")
    readonly_fields = ("created_at", "updated_at", "telegram_id", "last_login")
    ordering = ("-created_at",)
    list_per_page = 50
    list_select_related = ("department",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Shaxsiy ma'lumotlar",
            {"fields": ("full_name", "phone_number", "telegram_id")},
        ),
        (
            "Rol va bo'lim",
            {"fields": ("role", "department")},
        ),
        (
            "Ruxsatlar",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Sanalar",
            {"fields": ("last_login", "created_at", "updated_at")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "full_name",
                    "password1",
                    "password2",
                    "role",
                    "department",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    actions = ["make_boss", "make_head", "make_employee", "deactivate_users"]

    def make_boss(self, request, queryset):
        queryset.update(role=UserRole.BOSS)
        self.message_user(request, f"{queryset.count()} foydalanuvchiga 'Boshliq' roli berildi.")
    make_boss.short_description = "Boshliq rolini berish"

    def make_head(self, request, queryset):
        queryset.update(role=UserRole.HEAD)
        self.message_user(request, f"{queryset.count()} foydalanuvchiga 'Bo'lim boshlig'i' roli berildi.")
    make_head.short_description = "Bo'lim boshlig'i rolini berish"

    def make_employee(self, request, queryset):
        queryset.update(role=UserRole.EMPLOYEE)
        self.message_user(request, f"{queryset.count()} foydalanuvchiga 'Ishchi' roli berildi.")
    make_employee.short_description = "Ishchi rolini berish"

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} foydalanuvchi o'chirildi.")
    deactivate_users.short_description = "Foydalanuvchilarni o'chirish"
