from django.contrib import admin
from .models import Department


class DepartmentMemberInline(admin.TabularInline):
    from apps.users.models import User
    model = User
    fields = ("username", "full_name", "role", "is_active")
    readonly_fields = ("username", "full_name", "role", "is_active")
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "A'zo"
    verbose_name_plural = "A'zolar"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("department")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "get_head_name",
        "get_members_count",
        "get_active_tasks",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)
    list_per_page = 30

    def get_head_name(self, obj):
        head = obj.get_head()
        return head.get_display_name() if head else "—"
    get_head_name.short_description = "Boshlig'i"

    def get_members_count(self, obj):
        return obj.members.filter(is_active=True).count()
    get_members_count.short_description = "A'zolar"

    def get_active_tasks(self, obj):
        return obj.get_active_tasks_count()
    get_active_tasks.short_description = "Faol vazifalar"

    actions = ["activate_departments", "deactivate_departments"]

    def activate_departments(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} bo'lim faollashtirildi.")
    activate_departments.short_description = "Bo'limlarni faollashtirish"

    def deactivate_departments(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} bo'lim o'chirildi.")
    deactivate_departments.short_description = "Bo'limlarni o'chirish"
