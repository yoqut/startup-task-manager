from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdminOrAbove
from .models import AgentConfiguration, AgentExecutionLog, AgentType
from .serializers import AgentConfigSerializer, AgentExecutionLogSerializer


class AgentConfigViewSet(viewsets.ModelViewSet):
    serializer_class = AgentConfigSerializer
    permission_classes = [IsAdminOrAbove]
    http_method_names = ["get", "patch", "head", "options"]  # No create/delete via API

    def get_queryset(self):
        return AgentConfiguration.objects.for_company(self.request.company)

    @action(detail=True, methods=["post"], url_path="trigger")
    def trigger(self, request, pk=None):
        """Manually trigger an agent run."""
        config = self.get_object()
        if not config.is_enabled:
            return Response(
                {"error": "This agent is currently disabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task_description = request.data.get(
            "task_description",
            "Perform a general review and report on your domain.",
        )

        from apps.agents.tasks import run_agent_on_demand
        result = run_agent_on_demand.delay(
            company_id=str(request.company.id),
            agent_type=config.agent_type,
            task_description=task_description,
            user_id=str(request.user.id),
        )

        return Response(
            {"success": True, "task_id": result.id, "message": "Agent triggered."},
            status=status.HTTP_202_ACCEPTED,
        )


class AgentExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentExecutionLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["agent_type", "status", "trigger_source"]
    ordering = ["-started_at"]

    def get_queryset(self):
        return AgentExecutionLog.objects.for_company(self.request.company).select_related("triggered_by")
