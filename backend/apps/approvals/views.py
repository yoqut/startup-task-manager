from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from apps.accounts.permissions import IsManagerOrAbove
from .models import ApprovalRequest
from .serializers import ApprovalRequestSerializer


class ApprovalRequestViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ApprovalRequestSerializer
    permission_classes = [IsManagerOrAbove]
    filterset_fields = ["status", "agent_type", "action_category"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return ApprovalRequest.objects.for_company(self.request.company).select_related("decided_by")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        approval = self.get_object()
        if approval.status != ApprovalRequest.Status.PENDING:
            return Response(
                {"error": f"This request is already {approval.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if approval.is_expired:
            approval.status = ApprovalRequest.Status.EXPIRED
            approval.save(update_fields=["status"])
            return Response({"error": "This approval request has expired."}, status=status.HTTP_400_BAD_REQUEST)

        approval.status = ApprovalRequest.Status.APPROVED
        approval.decided_by = request.user
        approval.decided_at = timezone.now()
        approval.decision_comment = request.data.get("comment", "")
        approval.save()

        return Response({"success": True, "message": "Action approved."})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        approval = self.get_object()
        if approval.status != ApprovalRequest.Status.PENDING:
            return Response(
                {"error": f"This request is already {approval.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        approval.status = ApprovalRequest.Status.REJECTED
        approval.decided_by = request.user
        approval.decided_at = timezone.now()
        approval.decision_comment = request.data.get("comment", "")
        approval.save()

        return Response({"success": True, "message": "Action rejected."})

    @action(detail=False, methods=["get"])
    def pending(self, request):
        approvals = self.get_queryset().filter(
            status=ApprovalRequest.Status.PENDING,
            expires_at__gt=timezone.now(),
        )
        serializer = self.get_serializer(approvals, many=True)
        return Response(serializer.data)
