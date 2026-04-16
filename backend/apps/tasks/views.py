from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.accounts.permissions import IsManagerOrAbove
from .models import Task, TaskComment, Workflow
from .serializers import TaskSerializer, TaskListSerializer, TaskCommentSerializer, WorkflowSerializer


class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "priority", "department", "assigned_to"]
    search_fields = ["title", "description"]
    ordering_fields = ["due_date", "priority", "created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Task.objects.for_company(self.request.company).select_related(
            "assigned_to", "created_by", "ai_suggested_assignee"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return TaskListSerializer
        return TaskSerializer

    def perform_create(self, serializer):
        task = serializer.save(company=self.request.company, created_by=self.request.user)
        # Fire smart routing agent (async — task creation never fails if Celery is down)
        try:
            from apps.agents.tasks import route_new_task
            route_new_task.delay(str(task.id), str(task.company_id))
        except Exception:
            pass

    @action(detail=True, methods=["post"], url_path="report", permission_classes=[permissions.IsAuthenticated])
    def report(self, request, pk=None):
        """Submit a progress/completion report for a task."""
        from apps.reports.models import Report
        from apps.reports.serializers import ReportSerializer

        task = self.get_object()

        data = {
            "title":       request.data.get("title") or f"Hisobot: {task.title[:80]}",
            "body":        request.data.get("body", ""),
            "report_type": request.data.get("report_type", "progress"),
            "related_task": str(task.id),
        }
        serializer = ReportSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            company=request.company,
            sent_by=request.user,
            related_task=task,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request, pk=None):
        task = self.get_object()
        if request.method == "GET":
            qs = task.comments.select_related("author").all()
            serializer = TaskCommentSerializer(qs, many=True)
            return Response(serializer.data)
        # POST
        serializer = TaskCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(task=task, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="my-tasks")
    def my_tasks(self, request):
        tasks = self.get_queryset().filter(
            assigned_to=request.user
        ).exclude(status__in=[Task.Status.DONE, Task.Status.CANCELLED])
        serializer = TaskListSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        from django.utils import timezone
        tasks = self.get_queryset().filter(
            due_date__lt=timezone.now()
        ).exclude(status__in=[Task.Status.DONE, Task.Status.CANCELLED])
        serializer = TaskListSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def blocked(self, request):
        tasks = self.get_queryset().filter(status=Task.Status.BLOCKED)
        serializer = TaskListSerializer(tasks, many=True)
        return Response(serializer.data)


class WorkflowViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowSerializer
    permission_classes = [IsManagerOrAbove]

    def get_queryset(self):
        return Workflow.objects.for_company(self.request.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.company, created_by=self.request.user)
