from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from .models import ChatRoom, ChatMessage
from .serializers import ChatRoomSerializer, ChatMessageSerializer


class IsManagerOrAbove(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.is_manager_or_above)


class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer

    def get_permissions(self):
        # Creating/editing rooms requires manager+
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user    = self.request.user
        company = self.request.company
        qs = ChatRoom.objects.for_company(company).prefetch_related("org_units", "members")

        # Filter to rooms the user can actually access
        if user.is_admin_or_above:
            return qs   # admins see all rooms

        accessible = qs.filter(
            Q(type=ChatRoom.Type.COMPANY)                                     # company-wide
            | Q(type__in=[ChatRoom.Type.BRANCH, ChatRoom.Type.DEPARTMENT],    # user's dept in org_units
               org_units__pk=user.dept_id)
            | Q(members=user)                                                  # directly added
        ).distinct()
        return accessible

    def perform_create(self, serializer):
        room = serializer.save(company=self.request.company, created_by=self.request.user)
        # Auto-add creator as member (useful for DIRECT rooms)
        if room.type == ChatRoom.Type.DIRECT:
            room.members.add(self.request.user)

    # ── Message history ──────────────────────────────────────────────────────

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        room = self.get_object()
        if not room.can_access(request.user):
            raise PermissionDenied
        qs = room.messages.select_related("author").order_by("-created_at")[:50]
        # Return in chronological order
        msgs = list(reversed(list(qs)))
        return Response(ChatMessageSerializer(msgs, many=True).data)
