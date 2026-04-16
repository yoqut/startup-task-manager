from django.contrib import admin
from .models import AgentConfiguration, AgentExecutionLog, AgentPromptTemplate


@admin.register(AgentConfiguration)
class AgentConfigurationAdmin(admin.ModelAdmin):
    list_display = ["company", "agent_type", "parent_agent", "is_enabled", "autonomy_level", "daily_token_budget"]
    list_filter = ["agent_type", "is_enabled"]
    search_fields = ["company__name"]
    fields = [
        "company", "agent_type", "parent_agent", "is_enabled", "autonomy_level",
        "system_prompt", "custom_instructions", "daily_token_budget", "schedule_config",
    ]


@admin.register(AgentExecutionLog)
class AgentExecutionLogAdmin(admin.ModelAdmin):
    list_display = ["company", "agent_type", "status", "trigger_source", "confidence_score", "total_tokens", "started_at"]
    list_filter = ["agent_type", "status", "trigger_source"]
    search_fields = ["company__name", "task_description"]
    readonly_fields = ["id", "started_at", "input_context", "llm_response", "parsed_output", "actions_taken"]


@admin.register(AgentPromptTemplate)
class AgentPromptTemplateAdmin(admin.ModelAdmin):
    list_display = ["agent_type", "version", "is_active", "created_at"]
    list_filter = ["agent_type", "is_active"]
