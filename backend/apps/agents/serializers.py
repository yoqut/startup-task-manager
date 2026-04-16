from rest_framework import serializers
from .models import AgentConfiguration, AgentExecutionLog


class AgentConfigSerializer(serializers.ModelSerializer):
    agent_type_display = serializers.CharField(source="get_agent_type_display", read_only=True)
    parent_agent_type = serializers.CharField(
        source="parent_agent.agent_type", read_only=True, default=None
    )
    parent_agent_display = serializers.CharField(
        source="parent_agent.get_agent_type_display", read_only=True, default=None
    )
    child_agents = serializers.SerializerMethodField()

    department_ids   = serializers.PrimaryKeyRelatedField(
        source="departments", many=True, read_only=True
    )
    department_names = serializers.SerializerMethodField()

    class Meta:
        model = AgentConfiguration
        fields = [
            "id", "agent_type", "agent_type_display",
            "parent_agent", "parent_agent_type", "parent_agent_display",
            "child_agents",
            "is_enabled", "autonomy_level",
            "system_prompt", "custom_instructions",
            "departments", "department_ids", "department_names",
            "monitor_chats",
            "daily_token_budget", "schedule_config",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "agent_type", "parent_agent",
            "parent_agent_type", "parent_agent_display",
            "child_agents", "department_ids", "department_names",
            "created_at", "updated_at",
        ]

    def get_department_names(self, obj):
        return list(obj.departments.values_list("name", flat=True))

    def get_child_agents(self, obj):
        return [
            {"id": str(c.id), "agent_type": c.agent_type, "label": c.get_agent_type_display()}
            for c in obj.child_agents.all()
        ]


class AgentExecutionLogSerializer(serializers.ModelSerializer):
    agent_type_display = serializers.CharField(source="get_agent_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    triggered_by_name = serializers.CharField(source="triggered_by.full_name", read_only=True)

    class Meta:
        model = AgentExecutionLog
        fields = [
            "id", "agent_type", "agent_type_display", "status", "status_display",
            "trigger_source", "triggered_by", "triggered_by_name",
            "task_description", "parsed_output", "actions_taken",
            "confidence_score", "prompt_tokens", "completion_tokens", "total_tokens",
            "started_at", "completed_at", "duration_ms", "error_message",
        ]
        read_only_fields = fields
