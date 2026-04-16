"""
ContextBuilder — Assembles structured data context for each agent execution.
Pulls relevant DB records and formats them into a prompt-ready payload.
"""
import json
import logging
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger("apps.agents")


def build_company_context(company) -> dict:
    """Base context injected into every agent prompt."""
    return {
        "company_name": company.name,
        "industry": company.get_industry_display(),
        "employee_count": company.employee_count,
        "plan": company.plan,
        "timezone": company.timezone,
    }


def build_operations_context(company) -> dict:
    """
    Context for the Operations Agent.
    Pulls task statistics, overdue items, blocked tasks, team workload.
    """
    from apps.tasks.models import Task

    now = timezone.now()
    tasks_qs = Task.objects.for_company(company)

    # Aggregate task stats
    all_tasks = tasks_qs.exclude(
        status__in=[Task.Status.DONE, Task.Status.CANCELLED]
    ).select_related("assigned_to")

    overdue = [
        {
            "id": str(t.id),
            "title": t.title,
            "priority": t.priority,
            "assigned_to": t.assigned_to.full_name if t.assigned_to else "Unassigned",
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "department": t.department,
        }
        for t in all_tasks
        if t.is_overdue
    ][:20]  # Cap to 20 items to control token usage

    blocked = [
        {
            "id": str(t.id),
            "title": t.title,
            "blocker_reason": t.blocker_reason,
            "assigned_to": t.assigned_to.full_name if t.assigned_to else "Unassigned",
        }
        for t in all_tasks.filter(status=Task.Status.BLOCKED)
    ][:10]

    # Team workload
    from django.db.models import Count
    workload = list(
        all_tasks.values(
            "assigned_to__first_name", "assigned_to__last_name", "assigned_to__id"
        )
        .annotate(open_tasks=Count("id"))
        .order_by("-open_tasks")[:10]
    )

    # Status distribution
    status_counts = {}
    for status_val, _ in Task.Status.choices:
        status_counts[status_val] = tasks_qs.filter(status=status_val).count()

    return {
        "task_statistics": {
            "status_distribution": status_counts,
            "total_open": all_tasks.count(),
            "overdue_count": len(overdue),
            "blocked_count": len(blocked),
        },
        "overdue_tasks": overdue,
        "blocked_tasks": blocked,
        "team_workload": workload,
        "context_generated_at": now.isoformat(),
    }


def build_support_context(company) -> dict:
    """Context for the Customer Support Agent (placeholder for MVP)."""
    return {
        "support_enabled": False,
        "note": "Customer Support Agent context will be populated in Phase 2.",
    }


def build_sales_context(company) -> dict:
    """Context for the Sales Agent (placeholder for MVP)."""
    return {
        "sales_enabled": False,
        "note": "Sales Agent context will be populated in Phase 2.",
    }


def format_context_for_prompt(context: dict) -> str:
    """
    Serialize context dict to a clean JSON string for prompt injection.
    Keeps it readable and within token limits.
    """
    return json.dumps(context, indent=2, default=str, ensure_ascii=False)
