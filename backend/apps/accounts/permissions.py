"""
Custom DRF permission classes for RBAC.
"""
from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_owner


class IsAdminOrAbove(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin_or_above


class IsManagerOrAbove(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_manager_or_above


class SameCompanyOnly(BasePermission):
    """Ensures the object's company matches the request user's company."""

    def has_object_permission(self, request, view, obj):
        company_id = getattr(obj, "company_id", None)
        return str(company_id) == str(request.user.company_id)
