"""
Tenant Middleware — attaches the authenticated user's company to the request.

Uses SimpleLazyObject so that request.company is evaluated only when first
accessed — AFTER DRF's JWT authentication has resolved request.user.
Without lazy evaluation, request.user is still AnonymousUser at middleware
time and request.company would always be None.
"""
import logging
from django.utils.functional import SimpleLazyObject

logger = logging.getLogger("apps.tenants")


def _get_company(request):
    if request.user.is_authenticated and hasattr(request.user, "company"):
        return request.user.company
    return None


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.company = SimpleLazyObject(lambda: _get_company(request))
        return self.get_response(request)
