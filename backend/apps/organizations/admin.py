from django.contrib import admin
from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ["name", "type", "company", "parent", "head", "created_at"]
    list_filter   = ["type", "company"]
    search_fields = ["name"]
    raw_id_fields = ["head", "parent"]
