from django.http import JsonResponse
from django.views import View


class HealthCheckView(View):
    def get(self, request):
        from django.db import connection
        try:
            connection.ensure_connection()
            db_ok = True
        except Exception:
            db_ok = False

        from django.core.cache import cache
        try:
            cache.set("health_check", "ok", 5)
            redis_ok = cache.get("health_check") == "ok"
        except Exception:
            redis_ok = False

        status = 200 if (db_ok and redis_ok) else 503
        return JsonResponse(
            {
                "status": "ok" if status == 200 else "degraded",
                "database": "ok" if db_ok else "error",
                "redis": "ok" if redis_ok else "error",
            },
            status=status,
        )
