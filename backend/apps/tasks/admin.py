from django.contrib import admin
from .models import Task, TaskComment, Workflow


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "status", "priority", "department", "assigned_to", "due_date", "is_overdue"]
    list_filter = ["status", "priority", "department", "company"]
    search_fields = ["title", "description"]
    raw_id_fields = ["company", "assigned_to", "created_by", "parent_task"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ["task", "author", "is_ai_generated", "created_at"]
    list_filter = ["is_ai_generated"]


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "trigger_type", "action_type", "is_active", "executions_count"]
    list_filter = ["trigger_type", "action_type", "is_active"]
