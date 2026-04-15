import logging
from django.db.models import Count, Q, F
from asgiref.sync import sync_to_async
from .models import Department
from apps.tasks.models import TaskStatus

logger = logging.getLogger("apps.bot")


def get_all_active_departments():
    return Department.objects.filter(is_active=True).only("id", "name", "description").order_by("name")


def get_department_by_id(department_id: int) -> Department | None:
    return Department.objects.filter(id=department_id, is_active=True).first()


def get_department_summary(department_id: int) -> dict:
    dept = get_department_by_id(department_id)
    if not dept:
        return {}

    from apps.users.models import UserRole
    members = dept.members.filter(is_active=True)
    total_members = members.count()
    employees_count = members.filter(role=UserRole.EMPLOYEE).count()

    tasks = dept.task_instances.all()
    total_tasks = tasks.count()
    new_tasks = tasks.filter(status=TaskStatus.NEW).count()
    in_progress = tasks.filter(status=TaskStatus.IN_PROGRESS).count()
    completed = tasks.filter(status=TaskStatus.COMPLETED).count()
    blocked = tasks.filter(status=TaskStatus.BLOCKED).count()
    overdue = tasks.filter(status=TaskStatus.OVERDUE).count()

    from apps.reports.models import ReportStatus
    # Use a single aggregation query instead of multiple queries
    reports_data = dept.task_instances.aggregate(
        total=Count("reports"),
        accepted=Count("reports", filter=Q(reports__status=ReportStatus.ACCEPTED))
    )
    total_reports = reports_data["total"] or 0
    accepted_reports = reports_data["accepted"] or 0

    return {
        "department": dept,
        "total_members": total_members,
        "employees_count": employees_count,
        "total_tasks": total_tasks,
        "new_tasks": new_tasks,
        "in_progress": in_progress,
        "completed": completed,
        "blocked": blocked,
        "overdue": overdue,
        "total_reports": total_reports,
        "accepted_reports": accepted_reports,
    }


def get_global_summary() -> dict:
    from apps.tasks.models import TaskInstance
    from apps.reports.models import Report, ReportStatus
    from apps.users.models import User, UserRole

    total_departments = Department.objects.filter(is_active=True).count()
    total_employees = User.objects.filter(role=UserRole.EMPLOYEE, is_active=True).count()
    total_tasks = TaskInstance.objects.count()
    completed_tasks = TaskInstance.objects.filter(status=TaskStatus.COMPLETED).count()
    overdue_tasks = TaskInstance.objects.filter(status=TaskStatus.OVERDUE).count()
    active_tasks = TaskInstance.objects.filter(
        status__in=[TaskStatus.NEW, TaskStatus.IN_PROGRESS]
    ).count()
    total_reports = Report.objects.count()
    accepted_reports = Report.objects.filter(status=ReportStatus.ACCEPTED).count()
    pending_reports = Report.objects.filter(status=ReportStatus.SUBMITTED).count()

    return {
        "total_departments": total_departments,
        "total_employees": total_employees,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "overdue_tasks": overdue_tasks,
        "active_tasks": active_tasks,
        "total_reports": total_reports,
        "accepted_reports": accepted_reports,
        "pending_reports": pending_reports,
    }


# ---------------------------------------------------------------------------
# Async wrappers — use these inside AsyncTeleBot handlers (async context).
# ---------------------------------------------------------------------------

aget_department_by_id = sync_to_async(get_department_by_id)
aget_department_summary = sync_to_async(get_department_summary)
aget_global_summary = sync_to_async(get_global_summary)


@sync_to_async
def aget_all_active_departments() -> list:
    return list(get_all_active_departments())
