from rest_framework import serializers
from .models import Task, TaskComment, Workflow


class TaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model = TaskComment
        fields = ["id", "body", "author", "author_name", "is_ai_generated", "created_at"]
        read_only_fields = ["id", "author", "is_ai_generated", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()
    assigned_to_name = serializers.CharField(source="assigned_to.full_name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "title", "description", "status", "priority", "department",
            "assigned_to", "assigned_to_name", "created_by", "created_by_name",
            "parent_task", "due_date", "started_at", "completed_at", "estimated_hours",
            "ai_priority_score", "ai_suggested_assignee", "is_ai_created",
            "blocker_reason", "tags", "is_overdue", "comments",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "ai_priority_score", "ai_suggested_assignee",
            "is_ai_created", "is_overdue", "created_at", "updated_at",
        ]


class TaskListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views (no comments)."""
    is_overdue = serializers.ReadOnlyField()
    assigned_to_name = serializers.CharField(source="assigned_to.full_name", read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "title", "status", "priority", "department",
            "assigned_to", "assigned_to_name", "due_date", "is_overdue",
            "tags", "created_at", "updated_at",
        ]


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = [
            "id", "name", "description", "trigger_type", "trigger_conditions",
            "action_type", "action_config", "is_active", "executions_count",
            "last_triggered_at", "created_at",
        ]
        read_only_fields = ["id", "executions_count", "last_triggered_at", "created_at"]
