"""
AIManager — Root URL Configuration
All API routes are versioned under /api/v1/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


# ── Restrict Django admin to platform superusers only ───────────────────────
# Company owners (role=owner, is_staff=False) cannot access admin.
# Only platform engineers with is_superuser=True can.
class _SuperuserOnlyAdmin(admin.AdminSite):
    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser


admin.site.__class__ = _SuperuserOnlyAdmin
# ────────────────────────────────────────────────────────────────────────────

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # API v1
    path("api/v1/auth/",          include("apps.accounts.urls")),
    path("api/v1/tenants/",       include("apps.tenants.urls")),
    path("api/v1/tasks/",         include("apps.tasks.urls")),
    path("api/v1/agents/",        include("apps.agents.urls")),
    path("api/v1/approvals/",     include("apps.approvals.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/knowledge/",     include("apps.knowledge.urls")),
    path("api/v1/analytics/",     include("apps.analytics.urls")),
    path("api/v1/integrations/",  include("apps.integrations.urls")),
    path("api/v1/audit/",         include("apps.audit.urls")),
    path("api/v1/reports/",        include("apps.reports.urls")),
    path("api/v1/organizations/", include("apps.organizations.urls")),
    path("api/v1/chat/",          include("apps.chat.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
