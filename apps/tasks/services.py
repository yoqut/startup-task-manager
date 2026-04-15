import logging
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async
from .models import (
    TaskTemplate,
    TaskInstance,
    TaskStatusHistory,
    TaskStatus,
    TaskType,
    Priority,
    ReportFrequency,
    RecurrenceType,
)

logger = logging.getLogger("apps.tasks")


def create_task_template(
    creator,
    title: str,
    description: str,
    instructions: str,
    priority: str = Priority.MEDIUM,
    task_type: str = TaskType.ONE_TIME,
    recurrence_type: str = RecurrenceType.NONE,
    report_frequency: str = ReportFrequency.NONE,
    start_date=None,
    end_date=None,
    estimated_duration: int = None,
    attachments_allowed: bool = True,
    report_required: bool = True,
    assigned_department=None,
    assigned_user=None,
) -> TaskTemplate:
    if not assigned_department and not assigned_user:
        raise ValueError("Bo'lim yoki xodim ko'rsatilishi kerak.")

    from apps.users.models import UserRole
    if creator.role == UserRole.HEAD:
        if assigned_department and assigned_department.id != creator.department_id:
            raise PermissionError("Siz faqat o'z bo'limingizga vazifa bera olasiz.")
        if assigned_user and assigned_user.department_id != creator.department_id:
            raise PermissionError("Siz faqat o'z bo'limingiz xodimlariga vazifa bera olasiz.")

    template = TaskTemplate.objects.create(
        creator=creator,
        title=title,
        description=description,
        instructions=instructions,
        priority=priority,
        task_type=task_type,
        recurrence_type=recurrence_type,
        report_frequency=report_frequency,
        start_date=start_date or timezone.now().date(),
        end_date=end_date,
        estimated_duration=estimated_duration,
        attachments_allowed=attachments_allowed,
        report_required=report_required,
        assigned_department=assigned_department,
        assigned_user=assigned_user,
    )
    logger.info(f"TaskTemplate created: id={template.id}, title={title}, creator={creator.id}")
    return template


def create_task_instance_from_template(template: TaskTemplate) -> list[TaskInstance]:
    now    = timezone.now()
    due_at = _calculate_due_date(template.recurrence_type, now)

    if template.assigned_user:
        return [_create_single_instance(
            template=template,
            assigned_user=template.assigned_user,
            assigned_department=None,
            now=now,
            due_at=due_at,
        )]

    if template.assigned_department:
        from apps.users.models import UserRole
        employees = list(template.assigned_department.members.filter(
            role=UserRole.EMPLOYEE,
            is_active=True,
        ))
        if employees:
            period_start, period_end = _calculate_period(template.report_frequency, now)
            objs = [
                TaskInstance(
                    template=template,
                    creator=template.creator,
                    assigned_user=emp,
                    assigned_department=template.assigned_department,
                    title=template.title,
                    description=template.description,
                    instructions=template.instructions,
                    priority=template.priority,
                    status=TaskStatus.NEW,
                    due_at=due_at,
                    start_at=now,
                    report_required=template.report_required,
                    report_frequency=template.report_frequency,
                    attachments_allowed=template.attachments_allowed,
                    current_period_start=period_start,
                    current_period_end=period_end,
                )
                for emp in employees
            ]
            instances = TaskInstance.objects.bulk_create(objs)
            logger.info(
                "TaskInstances bulk-created from template: template=%d count=%d",
                template.id, len(instances),
            )
            return instances
        else:
            return [_create_single_instance(
                template=template,
                assigned_user=None,
                assigned_department=template.assigned_department,
                now=now,
                due_at=due_at,
            )]

    return []


def _create_single_instance(
    template: TaskTemplate,
    assigned_user,
    assigned_department,
    now,
    due_at,
) -> TaskInstance:
    period_start, period_end = _calculate_period(template.report_frequency, now)
    instance = TaskInstance.objects.create(
        template=template,
        creator=template.creator,
        assigned_user=assigned_user,
        assigned_department=assigned_department,
        title=template.title,
        description=template.description,
        instructions=template.instructions,
        priority=template.priority,
        status=TaskStatus.NEW,
        due_at=due_at,
        start_at=now,
        report_required=template.report_required,
        report_frequency=template.report_frequency,
        attachments_allowed=template.attachments_allowed,
        current_period_start=period_start,
        current_period_end=period_end,
    )
    logger.info(f"TaskInstance created from template: id={instance.id}, template={template.id}")
    return instance


def create_one_time_task(
    creator,
    title: str,
    description: str,
    instructions: str,
    priority: str = Priority.MEDIUM,
    due_at=None,
    report_required: bool = True,
    report_frequency: str = ReportFrequency.NONE,
    attachments_allowed: bool = True,
    assigned_user=None,
    assigned_department=None,
) -> list[TaskInstance]:
    if not assigned_user and not assigned_department:
        raise ValueError("Bo'lim yoki xodim ko'rsatilishi kerak.")

    from apps.users.models import UserRole
    if creator.role == UserRole.HEAD:
        if assigned_department and assigned_department.id != creator.department_id:
            raise PermissionError("Siz faqat o'z bo'limingizga vazifa bera olasiz.")
        if assigned_user and assigned_user.department_id != creator.department_id:
            raise PermissionError("Siz faqat o'z bo'limingiz xodimlariga vazifa bera olasiz.")

    now = timezone.now()
    instances = []

    if assigned_user:
        instance = TaskInstance.objects.create(
            creator=creator,
            assigned_user=assigned_user,
            assigned_department=assigned_department,
            title=title,
            description=description,
            instructions=instructions,
            priority=priority,
            status=TaskStatus.NEW,
            due_at=due_at,
            start_at=now,
            report_required=report_required,
            report_frequency=report_frequency,
            attachments_allowed=attachments_allowed,
        )
        instances.append(instance)
    elif assigned_department:
        employees = list(assigned_department.members.filter(
            role=UserRole.EMPLOYEE,
            is_active=True,
        ))
        if employees:
            objs = [
                TaskInstance(
                    creator=creator,
                    assigned_user=emp,
                    assigned_department=assigned_department,
                    title=title,
                    description=description,
                    instructions=instructions,
                    priority=priority,
                    status=TaskStatus.NEW,
                    due_at=due_at,
                    start_at=now,
                    report_required=report_required,
                    report_frequency=report_frequency,
                    attachments_allowed=attachments_allowed,
                )
                for emp in employees
            ]
            instances = TaskInstance.objects.bulk_create(objs)
        else:
            instance = TaskInstance.objects.create(
                creator=creator,
                assigned_user=None,
                assigned_department=assigned_department,
                title=title,
                description=description,
                instructions=instructions,
                priority=priority,
                status=TaskStatus.NEW,
                due_at=due_at,
                start_at=now,
                report_required=report_required,
                report_frequency=report_frequency,
                attachments_allowed=attachments_allowed,
            )
            instances.append(instance)

    logger.info(
        f"One-time tasks created: count={len(instances)}, creator={creator.id}, title={title}"
    )
    return instances


@transaction.atomic
def change_task_status(
    task: TaskInstance,
    new_status: str,
    changed_by,
    comment: str = "",
) -> TaskInstance:
    allowed_transitions = {
        TaskStatus.NEW: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
        TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED, TaskStatus.BLOCKED, TaskStatus.CANCELLED],
        TaskStatus.BLOCKED: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
        TaskStatus.OVERDUE: [TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED],
        TaskStatus.COMPLETED: [],
        TaskStatus.CANCELLED: [],
    }

    from apps.users.models import UserRole
    if changed_by.role not in [UserRole.BOSS, UserRole.HEAD]:
        if new_status == TaskStatus.CANCELLED:
            raise PermissionError("Siz vazifani bekor qila olmaysiz.")

    if new_status not in allowed_transitions.get(task.status, []):
        raise ValueError(
            f"'{task.get_status_display()}' holatdan '{TaskStatus(new_status).label}' holatga o'tish mumkin emas."
        )

    old_status = task.status
    task.status = new_status
    if new_status == TaskStatus.COMPLETED:
        task.completed_at = timezone.now()
    task.save(update_fields=["status", "completed_at", "updated_at"])

    TaskStatusHistory.objects.create(
        task=task,
        changed_by=changed_by,
        old_status=old_status,
        new_status=new_status,
        comment=comment,
    )

    logger.info(
        f"Task status changed: task={task.id}, {old_status} -> {new_status}, by={changed_by.id}"
    )
    return task


def get_user_tasks(user, status_filter: str = None):
    qs = TaskInstance.objects.filter(
        assigned_user=user,
    ).only(
        "id", "title", "status", "priority", "due_at", "created_at", "is_overdue"
    ).order_by("-created_at")
    if status_filter:
        qs = qs.filter(status=status_filter)
    return qs


def get_active_tasks_for_user(user):
    return TaskInstance.objects.filter(
        assigned_user=user,
        status__in=[TaskStatus.NEW, TaskStatus.IN_PROGRESS]
    ).select_related("creator", "assigned_department").order_by("-created_at")


def get_overdue_tasks_for_user(user):
    return TaskInstance.objects.filter(
        assigned_user=user,
        status=TaskStatus.OVERDUE
    ).select_related("creator", "assigned_department").order_by("-created_at")


def get_completed_tasks_for_user(user):
    return TaskInstance.objects.filter(
        assigned_user=user,
        status=TaskStatus.COMPLETED
    ).select_related("creator", "assigned_department").order_by("-created_at")


def get_department_tasks(department_id: int, status_filter: str = None):
    qs = TaskInstance.objects.filter(
        assigned_department_id=department_id,
    ).select_related("creator", "assigned_user").order_by("-created_at").defer("description", "instructions")
    if status_filter:
        qs = qs.filter(status=status_filter)
    return qs


def get_all_tasks(status_filter: str = None, department_id: int = None, user_id: int = None):
    qs = TaskInstance.objects.select_related(
        "creator", "assigned_user", "assigned_department"
    ).defer("description", "instructions").order_by("-created_at")
    if status_filter:
        qs = qs.filter(status=status_filter)
    if department_id:
        qs = qs.filter(assigned_department_id=department_id)
    if user_id:
        qs = qs.filter(assigned_user_id=user_id)
    return qs


def get_overdue_tasks_for_department(department_id: int):
    return TaskInstance.objects.filter(
        assigned_department_id=department_id,
        status=TaskStatus.OVERDUE,
    ).select_related("assigned_user").defer("description", "instructions").order_by("-due_at")


def _calculate_due_date(recurrence_type: str, from_date):
    if recurrence_type == RecurrenceType.DAILY:
        return from_date + timedelta(days=1)
    elif recurrence_type == RecurrenceType.WEEKLY:
        return from_date + timedelta(weeks=1)
    elif recurrence_type == RecurrenceType.MONTHLY:
        return from_date + timedelta(days=30)
    elif recurrence_type == RecurrenceType.YEARLY:
        return from_date + timedelta(days=365)
    return None


def _calculate_period(report_frequency: str, from_date):
    if report_frequency == ReportFrequency.DAILY:
        start = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return start, end
    elif report_frequency == ReportFrequency.WEEKLY:
        start = from_date - timedelta(days=from_date.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(weeks=1)
        return start, end
    elif report_frequency == ReportFrequency.MONTHLY:
        start = from_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if from_date.month == 12:
            end = start.replace(year=from_date.year + 1, month=1)
        else:
            end = start.replace(month=from_date.month + 1)
        return start, end
    elif report_frequency == ReportFrequency.YEARLY:
        start = from_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=from_date.year + 1)
        return start, end
    return None, None


# ---------------------------------------------------------------------------
# Async wrappers — use these inside AsyncTeleBot handlers (async context).
# Functions returning QuerySets are wrapped to return lists so the DB
# evaluation happens safely inside the thread pool.
# ---------------------------------------------------------------------------

acreate_one_time_task = sync_to_async(create_one_time_task)
acreate_task_template = sync_to_async(create_task_template)
acreate_task_instance_from_template = sync_to_async(create_task_instance_from_template)
achange_task_status = sync_to_async(change_task_status)


@sync_to_async
def aget_task_instance(task_id: int, **filter_kwargs) -> TaskInstance | None:
    """Fetch a single TaskInstance with related objects pre-loaded."""
    return (
        TaskInstance.objects
        .filter(id=task_id, **filter_kwargs)
        .select_related("assigned_user", "assigned_department", "creator")
        .first()
    )


@sync_to_async
def aget_user_tasks(user, status_filter: str = None) -> list:
    return list(get_user_tasks(user, status_filter))


@sync_to_async
def aget_active_tasks_for_user(user) -> list:
    return list(get_active_tasks_for_user(user))


@sync_to_async
def aget_completed_tasks_for_user(user) -> list:
    return list(get_completed_tasks_for_user(user))


@sync_to_async
def aget_overdue_tasks_for_user(user) -> list:
    return list(get_overdue_tasks_for_user(user))


@sync_to_async
def aget_department_tasks(department_id: int, status_filter: str = None) -> list:
    return list(get_department_tasks(department_id, status_filter))


@sync_to_async
def aget_all_tasks(status_filter: str = None, department_id: int = None, user_id: int = None) -> list:
    return list(get_all_tasks(status_filter=status_filter, department_id=department_id, user_id=user_id))


@sync_to_async
def aget_overdue_tasks_for_department(department_id: int) -> list:
    return list(get_overdue_tasks_for_department(department_id))
