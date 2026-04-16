from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models as db_models

from .models import Report, ReportComment
from .serializers import ReportSerializer, ReportListSerializer, ReportCommentSerializer


class ReportViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs   = Report.objects.for_company(self.request.company).select_related("sent_by", "sent_to")

        # Owner / Admin → see every report in the company
        if user.is_admin_or_above:
            return qs

        # Manager → see reports sent to them, or from their department, or their own
        if user.is_manager_or_above:
            return qs.filter(
                db_models.Q(sent_to=user) |
                db_models.Q(sent_by=user) |
                db_models.Q(department=user.department, sent_to__isnull=True)
            ).distinct()

        # Member / Viewer → only their own sent reports
        return qs.filter(sent_by=user)

    def get_serializer_class(self):
        if self.action == "list":
            return ReportListSerializer
        return ReportSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(
            company=self.request.company,
            sent_by=user,
            department=user.department or "",
        )

    @action(detail=True, methods=["post"], url_path="comments")
    def add_comment(self, request, pk=None):
        report = self.get_object()
        # Auto-mark report as read when a non-author (manager) replies
        if report.status == Report.Status.SENT and request.user != report.sent_by:
            report.status = Report.Status.READ
            report.save(update_fields=["status"])
        serializer = ReportCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(report=report, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="acknowledge")
    def acknowledge(self, request, pk=None):
        report = self.get_object()
        report.status = Report.Status.ACKNOWLEDGED
        report.save(update_fields=["status"])
        return Response({"success": True})
