import logging
import os
import uuid
from pathlib import Path
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async
from .models import Report, ReportAttachment, ReportStatus, FileType
from apps.tasks.models import TaskInstance, TaskStatus

logger = logging.getLogger("apps.reports")


def create_report(
    task: TaskInstance,
    employee,
    text: str = None,
) -> Report:
    if task.assigned_user and task.assigned_user_id != employee.id:
        raise PermissionError("Bu vazifa sizga tayinlanmagan.")

    with transaction.atomic():
        report = Report.objects.create(
            task=task,
            employee=employee,
            text=text,
            status=ReportStatus.SUBMITTED,
            submitted_at=timezone.now(),
        )
    logger.info(f"Report created: id={report.id}, task={task.id}, employee={employee.id}")
    return report


def add_attachment_from_file(
    report: Report,
    file_content: bytes,
    original_name: str,
    file_type: str,
    telegram_file_id: str = "",
) -> ReportAttachment:
    if not report.task.attachments_allowed:
        raise ValueError("Bu vazifa uchun ilova yuklash ruxsat etilmagan.")

    safe_name = _safe_filename(original_name)
    rel_path = os.path.join(
        "reports",
        str(report.task_id),
        str(report.employee_id),
        str(timezone.now().year),
        str(timezone.now().month),
        safe_name,
    )
    full_path = Path(settings.MEDIA_ROOT) / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    with open(full_path, "wb") as f:
        f.write(file_content)

    attachment = ReportAttachment.objects.create(
        report=report,
        file=rel_path,
        file_type=file_type,
        original_name=original_name[:255],
        telegram_file_id=telegram_file_id,
    )
    logger.info(f"Attachment added: report={report.id}, file={original_name}")
    return attachment


def get_task_reports(task_id: int):
    return Report.objects.filter(
        task_id=task_id
    ).select_related("employee", "reviewed_by").prefetch_related("attachments").order_by("-submitted_at")


def get_employee_reports(employee_id: int, task_id: int = None):
    qs = Report.objects.filter(employee_id=employee_id).select_related("task")
    if task_id:
        qs = qs.filter(task_id=task_id)
    return qs.order_by("-submitted_at")


def get_department_reports(department_id: int, status: str = None):
    qs = Report.objects.filter(
        task__assigned_department_id=department_id
    ).select_related("task", "employee").defer("text").order_by("-submitted_at")
    if status:
        qs = qs.filter(status=status)
    return qs


def get_all_reports(status: str = None, department_id: int = None):
    qs = Report.objects.select_related("task", "employee", "reviewed_by").defer("text").order_by("-submitted_at")
    if status:
        qs = qs.filter(status=status)
    if department_id:
        qs = qs.filter(task__assigned_department_id=department_id)
    return qs


def accept_report(report: Report, reviewer, comment: str = "") -> Report:
    report.accept(reviewer, comment)
    logger.info(f"Report accepted: id={report.id}, by={reviewer.id}")
    return report


def reject_report(report: Report, reviewer, comment: str) -> Report:
    if not comment:
        raise ValueError("Rad etish uchun izoh kiritish majburiy.")
    report.reject(reviewer, comment)
    logger.info(f"Report rejected: id={report.id}, by={reviewer.id}")
    return report


def get_pending_reports_for_manager(manager) -> list:
    from apps.users.models import UserRole
    if manager.role == UserRole.BOSS:
        return Report.objects.filter(
            status=ReportStatus.SUBMITTED
        ).select_related("task", "employee", "task__assigned_department").defer("text").order_by("-submitted_at")
    elif manager.role == UserRole.HEAD and manager.department_id:
        return Report.objects.filter(
            status=ReportStatus.SUBMITTED,
            task__assigned_department_id=manager.department_id,
        ).select_related("task", "employee").defer("text").order_by("-submitted_at")
    return Report.objects.none()


def _safe_filename(original: str) -> str:
    ext = Path(original).suffix[:10]
    return f"{uuid.uuid4().hex}{ext}"


# ---------------------------------------------------------------------------
# Async wrappers — use these inside AsyncTeleBot handlers (async context).
# ---------------------------------------------------------------------------

acreate_report = sync_to_async(create_report)
aadd_attachment_from_file = sync_to_async(add_attachment_from_file)
aaccept_report = sync_to_async(accept_report)
areject_report = sync_to_async(reject_report)


@sync_to_async
def aget_report_by_id(report_id: int) -> Report | None:
    return (
        Report.objects
        .filter(id=report_id)
        .select_related("task", "employee", "reviewed_by")
        .prefetch_related("attachments")
        .first()
    )


@sync_to_async
def aget_pending_reports_for_manager(manager) -> list:
    return list(get_pending_reports_for_manager(manager))


@sync_to_async
def aget_all_reports(status: str = None, department_id: int = None) -> list:
    return list(get_all_reports(status=status, department_id=department_id))


@sync_to_async
def aget_department_reports(department_id: int, status: str = None) -> list:
    return list(get_department_reports(department_id, status=status))


@sync_to_async
def aget_task_reports(task_id: int) -> list:
    return list(get_task_reports(task_id))
