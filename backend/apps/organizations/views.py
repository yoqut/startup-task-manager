from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from .models import Department
from .serializers import DepartmentSerializer

User = get_user_model()


class IsAdminOrOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_or_above)


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer

    def get_permissions(self):
        write_actions = {"create", "update", "partial_update", "destroy",
                         "assign_members", "remove_member", "set_head"}
        if self.action in write_actions:
            return [IsAuthenticated(), IsAdminOrOwner()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return (
            Department.objects
            .for_company(self.request.company)
            .select_related("parent", "head")
            .prefetch_related("children")
            .annotate(member_count=Count("members"))
            .order_by("name")
        )

    def perform_create(self, serializer):
        company = self.request.company
        if serializer.validated_data.get("type") == Department.Type.HEAD_OFFICE:
            if Department.objects.filter(company=company, type=Department.Type.HEAD_OFFICE).exists():
                raise ValidationError({"type": "A head office already exists for this company."})
        serializer.save(company=company)

    # ── Members ──────────────────────────────────────────────────────────────

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        dept = self.get_object()
        # Lazy import to avoid circular
        from apps.accounts.serializers import UserSerializer
        qs = dept.members.filter(company=request.company).select_related("dept")
        return Response(UserSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="assign-members")
    def assign_members(self, request, pk=None):
        dept = self.get_object()
        user_ids = request.data.get("user_ids", [])
        updated = User.objects.filter(
            company=request.company, id__in=user_ids
        ).update(dept=dept)
        return Response({"assigned": updated})

    @action(detail=True, methods=["post"], url_path="remove-member")
    def remove_member(self, request, pk=None):
        dept = self.get_object()
        user_id = request.data.get("user_id")
        updated = User.objects.filter(
            company=request.company, id=user_id, dept=dept
        ).update(dept=None)
        return Response({"removed": updated})

    @action(detail=True, methods=["post"], url_path="set-head")
    def set_head(self, request, pk=None):
        dept = self.get_object()
        user_id = request.data.get("user_id")  # null to clear
        if user_id:
            try:
                head = User.objects.get(id=user_id, company=request.company)
            except User.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            dept.head = head
        else:
            dept.head = None
        dept.save(update_fields=["head"])
        return Response(DepartmentSerializer(dept).data)
