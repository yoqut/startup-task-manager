"""
Inline keyboard builders — all built with InlineKeyboardBuilder from core.

Button style guide (Telegram Bot API `style` field):
  "primary" (blue)  — main navigation, primary actions
  "success" (green) — confirmations, positive actions (start, accept, done)
  "danger"  (red)   — destructive / cancel / reject actions
  None              — neutral: back, pagination, info labels
"""
from telebot.callback_data import CallbackData
from telebot.types import InlineKeyboardMarkup

from core.keyboards import InlineKeyboardBuilder

# ---------------------------------------------------------------------------
# CallbackData factories
# ---------------------------------------------------------------------------
task_cb        = CallbackData("action",  "task_id",   prefix="task")
task_status_cb = CallbackData("task_id", "status",    prefix="tstatus")
report_cb      = CallbackData("action",  "report_id", prefix="report")
page_cb        = CallbackData("entity",  "flt", "page", prefix="pg")
admin_user_cb  = CallbackData("action",  "user_id",   prefix="auser")


# ---------------------------------------------------------------------------
# Main-menu inline keyboards  (role-based)
# ---------------------------------------------------------------------------

def get_main_menu(user) -> InlineKeyboardMarkup:
    """Return the role-appropriate inline main menu for *user*."""
    if user is None or not user.has_role:
        return _main_menu_no_role()
    from apps.users.models import UserRole
    if user.role == UserRole.BOSS:
        return _main_menu_boss()
    if user.role == UserRole.HEAD:
        return _main_menu_head()
    return _main_menu_employee()


def _main_menu_no_role() -> InlineKeyboardMarkup:
    return (
        InlineKeyboardBuilder()
        .button("ℹ️ Profil",  callback_data="menu:profile")
        .button("❓ Yordam",  callback_data="menu:help")
        .build()
    )


def _main_menu_employee() -> InlineKeyboardMarkup:
    return (
        InlineKeyboardBuilder()
        .button("📋 Vazifalarim",       callback_data="menu:tasks",         style="primary")
        .button("📊 Hisobot yuborish",  callback_data="menu:submit_report", style="primary")
        .row()
        .button("ℹ️ Profil",            callback_data="menu:profile")
        .button("❓ Yordam",            callback_data="menu:help")
        .build()
    )


def _main_menu_head() -> InlineKeyboardMarkup:
    return (
        InlineKeyboardBuilder()
        .button("📋 Vazifalarim",    callback_data="menu:tasks",      style="primary")
        .button("📝 Yangi vazifa",   callback_data="menu:new_task",   style="success")
        .row()
        .button("📊 Hisobotlar",     callback_data="menu:reports",    style="primary")
        .button("👥 Bo'lim",         callback_data="menu:department", style="primary")
        .row()
        .button("ℹ️ Profil",         callback_data="menu:profile")
        .button("❓ Yordam",         callback_data="menu:help")
        .build()
    )


def _main_menu_boss() -> InlineKeyboardMarkup:
    return (
        InlineKeyboardBuilder()
        .button("📋 Barcha vazifalar",   callback_data="menu:tasks",      style="primary")
        .button("📝 Yangi vazifa",       callback_data="menu:new_task",   style="success")
        .row()
        .button("📊 Barcha hisobotlar",  callback_data="menu:reports",    style="primary")
        .button("👥 Foydalanuvchilar",   callback_data="menu:users",      style="primary")
        .row()
        .button("📢 Xabar yuborish",     callback_data="menu:broadcast",  style="primary")
        .button("📈 Statistika",         callback_data="menu:statistics", style="primary")
        .row()
        .button("ℹ️ Profil",             callback_data="menu:profile")
        .build()
    )


# ---------------------------------------------------------------------------
# Generic wizard keyboards  (cancel / skip+cancel / done+cancel)
# ---------------------------------------------------------------------------

def wizard_cancel_inl(cancel_cb: str) -> InlineKeyboardMarkup:
    """Single cancel button (danger)."""
    return (
        InlineKeyboardBuilder()
        .button("❌ Bekor qilish", callback_data=cancel_cb, style="danger")
        .build()
    )


def wizard_skip_cancel_inl(skip_cb: str, cancel_cb: str) -> InlineKeyboardMarkup:
    """Skip (neutral) + Cancel (danger)."""
    return (
        InlineKeyboardBuilder()
        .button("⏩ O'tkazib yuborish", callback_data=skip_cb)
        .button("❌ Bekor qilish",      callback_data=cancel_cb, style="danger")
        .build()
    )


def wizard_done_cancel_inl(done_cb: str, cancel_cb: str) -> InlineKeyboardMarkup:
    """Done (success) + Cancel (danger)."""
    return (
        InlineKeyboardBuilder()
        .button("✅ Tayyor",         callback_data=done_cb,    style="success")
        .button("❌ Bekor qilish",   callback_data=cancel_cb,  style="danger")
        .build()
    )


# ---------------------------------------------------------------------------
# Welcome / tariff
# ---------------------------------------------------------------------------

def tariff_inl(_lang: str = "uz") -> InlineKeyboardMarkup:
    return (
        InlineKeyboardBuilder()
        .button("🟢 Standard", callback_data="plans:standard", style="primary")
        .row()
        .button("🚀 Pro",      callback_data="plans:pro",      style="primary")
        .row()
        .button("💎 Premium",  callback_data="plans:premium",  style="primary")
        .build()
    )


# ---------------------------------------------------------------------------
# Task list  (paginated)
# ---------------------------------------------------------------------------

def task_list_inl(
    tasks: list,
    page: int = 0,
    total_pages: int = 1,
    filter_key: str = "all",
) -> InlineKeyboardMarkup:
    status_icons = {
        "new": "🆕", "in_progress": "⚙️", "completed": "✅",
        "blocked": "🔴", "cancelled": "❌", "overdue": "⚠️",
    }
    builder = InlineKeyboardBuilder()

    for task in tasks:
        icon  = status_icons.get(task.status, "📋")
        title = task.title[:42] if len(task.title) > 42 else task.title
        builder.button(
            f"{icon} {title}",
            callback_data=task_cb.new(action="view", task_id=str(task.id)),
        ).row()

    # Pagination row
    if page > 0:
        builder.button(
            "◀️",
            callback_data=page_cb.new(entity="tasks", flt=filter_key, page=str(page - 1)),
        )
    builder.button(f"· {page + 1}/{total_pages} ·", callback_data="noop")
    if page < total_pages - 1:
        builder.button(
            "▶️",
            callback_data=page_cb.new(entity="tasks", flt=filter_key, page=str(page + 1)),
        )
    builder.row()
    builder.button("🔍 Filtr",    callback_data=f"tasks_filter:{filter_key}", style="primary")
    builder.row()
    builder.button("🔙 Orqaga",   callback_data="back_to_main")
    return builder.build()


# ---------------------------------------------------------------------------
# Task filter selector
# ---------------------------------------------------------------------------

def task_filter_inl(current: str = "all") -> InlineKeyboardMarkup:
    filters = [
        ("all",         "📋 Barchasi"),
        ("new",         "🆕 Yangi"),
        ("in_progress", "⚙️ Jarayonda"),
        ("completed",   "✅ Bajarildi"),
        ("overdue",     "⚠️ Muddati o'tgan"),
    ]
    builder = InlineKeyboardBuilder()
    for i, (key, label) in enumerate(filters):
        text  = f"✓ {label}" if key == current else label
        style = "primary" if key == current else None
        builder.button(text, callback_data=page_cb.new(entity="tasks", flt=key, page="0"), style=style)
        if i % 2 == 1:
            builder.row()
    builder.row()
    builder.button("🔙 Orqaga", callback_data="back_to_tasks")
    return builder.build()


# ---------------------------------------------------------------------------
# Task detail actions
# ---------------------------------------------------------------------------

def task_detail_inl(task, user_role: str = "employee") -> InlineKeyboardMarkup:
    from apps.tasks.models import TaskStatus
    from apps.users.models import UserRole

    builder = InlineKeyboardBuilder()

    if task.status == TaskStatus.NEW:
        builder.button(
            "▶️ Boshlash",
            callback_data=task_status_cb.new(task_id=str(task.id), status="in_progress"),
            style="success",
        ).row()

    if task.status == TaskStatus.IN_PROGRESS:
        builder.button(
            "✅ Bajarildi",
            callback_data=task_status_cb.new(task_id=str(task.id), status="completed"),
            style="success",
        ).button(
            "🔴 Bloklandi",
            callback_data=task_status_cb.new(task_id=str(task.id), status="blocked"),
            style="danger",
        ).row()

    if task.status in (TaskStatus.BLOCKED, TaskStatus.OVERDUE):
        builder.button(
            "▶️ Davom etish",
            callback_data=task_status_cb.new(task_id=str(task.id), status="in_progress"),
            style="primary",
        ).row()

    if (
        task.status in [TaskStatus.NEW, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED]
        and user_role in [UserRole.BOSS, UserRole.HEAD]
    ):
        builder.button(
            "❌ Bekor qilish",
            callback_data=task_status_cb.new(task_id=str(task.id), status="cancelled"),
            style="danger",
        ).row()

    if task.status in [TaskStatus.IN_PROGRESS, TaskStatus.OVERDUE] and task.report_required:
        builder.button(
            "📊 Hisobot yuborish",
            callback_data=task_cb.new(action="report", task_id=str(task.id)),
            style="primary",
        ).row()

    builder.button("🔙 Orqaga", callback_data="back_to_tasks")
    return builder.build()


# ---------------------------------------------------------------------------
# Priority picker
# ---------------------------------------------------------------------------

def priority_inl() -> InlineKeyboardMarkup:
    priorities = [
        ("low",    "⬇️ Past",        None),
        ("medium", "➡️ O'rta",       None),
        ("high",   "⬆️ Yuqori",      "primary"),
        ("urgent", "🚨 Shoshilinch", "danger"),
    ]
    builder = InlineKeyboardBuilder()
    for i, (key, label, style) in enumerate(priorities):
        builder.button(label, callback_data=f"priority:{key}", style=style)
        if i % 2 == 1:
            builder.row()
    builder.row()
    builder.button("❌ Bekor qilish", callback_data="cancel_task_creation", style="danger")
    return builder.build()


# ---------------------------------------------------------------------------
# Task creation — assign type
# ---------------------------------------------------------------------------

def assign_type_inl() -> InlineKeyboardMarkup:
    return (
        InlineKeyboardBuilder()
        .button("👤 Xodimga tayinlash",  callback_data="assign:user",       style="primary")
        .row()
        .button("🏢 Bo'limga tayinlash", callback_data="assign:department",  style="primary")
        .row()
        .button("❌ Bekor qilish",       callback_data="cancel_task_creation", style="danger")
        .build()
    )


# ---------------------------------------------------------------------------
# Department / Employee lists for task creation
# ---------------------------------------------------------------------------

def departments_inl(departments: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for dept in departments:
        builder.button(
            f"🏢 {dept.name}",
            callback_data=f"dept:{dept.id}",
            style="primary",
        ).row()
    builder.button("❌ Bekor qilish", callback_data="cancel_task_creation", style="danger")
    return builder.build()


def employees_inl(employees: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for emp in employees:
        dept_name = emp.department.name if emp.department else "—"
        builder.button(
            f"👤 {emp.full_name or emp.username} ({dept_name})",
            callback_data=f"emp:{emp.id}",
            style="primary",
        ).row()
    builder.button("❌ Bekor qilish", callback_data="cancel_task_creation", style="danger")
    return builder.build()


# ---------------------------------------------------------------------------
# Task creation — confirm
# ---------------------------------------------------------------------------

def confirm_task_inl() -> InlineKeyboardMarkup:
    return (
        InlineKeyboardBuilder()
        .button("✅ Tasdiqlash",   callback_data="confirm:yes:task", style="success")
        .button("❌ Bekor qilish", callback_data="confirm:no:task",  style="danger")
        .build()
    )


# ---------------------------------------------------------------------------
# Report list  (paginated)
# ---------------------------------------------------------------------------

def report_list_inl(
    reports: list,
    page: int = 0,
    total_pages: int = 1,
    mode: str = "pending",
) -> InlineKeyboardMarkup:
    status_icons = {"submitted": "📤", "accepted": "✅", "rejected": "❌"}
    builder = InlineKeyboardBuilder()

    for report in reports:
        icon = status_icons.get(report.status, "📊")
        emp  = report.employee.get_display_name()[:20] if report.employee else "—"
        ttl  = report.task.title[:22] if report.task else "—"
        builder.button(
            f"{icon} {emp}: {ttl}",
            callback_data=report_cb.new(action="view", report_id=str(report.id)),
        ).row()

    if page > 0:
        builder.button(
            "◀️",
            callback_data=page_cb.new(entity="reports", flt=mode, page=str(page - 1)),
        )
    builder.button(f"· {page + 1}/{total_pages} ·", callback_data="noop")
    if page < total_pages - 1:
        builder.button(
            "▶️",
            callback_data=page_cb.new(entity="reports", flt=mode, page=str(page + 1)),
        )
    builder.row()
    builder.button("🔙 Orqaga", callback_data="back_to_main")
    return builder.build()


# ---------------------------------------------------------------------------
# Report detail — review actions
# ---------------------------------------------------------------------------

def report_detail_inl(report, can_review: bool = False) -> InlineKeyboardMarkup:
    from apps.reports.models import ReportStatus
    builder = InlineKeyboardBuilder()
    if can_review and report.status == ReportStatus.SUBMITTED:
        builder.button(
            "✅ Qabul",
            callback_data=report_cb.new(action="accept", report_id=str(report.id)),
            style="success",
        ).button(
            "❌ Rad etish",
            callback_data=report_cb.new(action="reject", report_id=str(report.id)),
            style="danger",
        ).row()
    builder.button("🔙 Orqaga", callback_data="back_to_reports")
    return builder.build()


# ---------------------------------------------------------------------------
# Report — task selector for quick report from task detail
# ---------------------------------------------------------------------------

def task_report_select_inl(tasks: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for task in tasks:
        builder.button(
            f"📋 {task.title[:50]}",
            callback_data=task_cb.new(action="select_for_report", task_id=str(task.id)),
            style="primary",
        ).row()
    builder.button("❌ Bekor qilish", callback_data="cancel_report", style="danger")
    return builder.build()


# ---------------------------------------------------------------------------
# Broadcast confirm
# ---------------------------------------------------------------------------

def confirm_broadcast_inl() -> InlineKeyboardMarkup:
    return (
        InlineKeyboardBuilder()
        .button("✅ Yuborish",     callback_data="broadcast:confirm", style="success")
        .button("❌ Bekor qilish", callback_data="broadcast:cancel",  style="danger")
        .build()
    )


# ---------------------------------------------------------------------------
# Users list (BOSS only, paginated)
# ---------------------------------------------------------------------------

def users_list_inl(users: list, page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    role_icons = {"boss": "👑", "head": "🏅", "employee": "👤"}
    builder = InlineKeyboardBuilder()

    for u in users:
        icon = role_icons.get(u.role or "", "👤")
        dept = u.department.name[:15] if u.department else "—"
        builder.button(
            f"{icon} {u.get_display_name()[:25]} ({dept})",
            callback_data=admin_user_cb.new(action="view", user_id=str(u.id)),
        ).row()

    if page > 0:
        builder.button(
            "◀️",
            callback_data=page_cb.new(entity="users", flt="all", page=str(page - 1)),
        )
    builder.button(f"· {page + 1}/{total_pages} ·", callback_data="noop")
    if page < total_pages - 1:
        builder.button(
            "▶️",
            callback_data=page_cb.new(entity="users", flt="all", page=str(page + 1)),
        )
    builder.row()
    builder.button("🔙 Orqaga", callback_data="back_to_main")
    return builder.build()


# ---------------------------------------------------------------------------
# User detail — back button
# ---------------------------------------------------------------------------

def user_detail_inl() -> InlineKeyboardMarkup:
    return (
        InlineKeyboardBuilder()
        .button("🔙 Orqaga", callback_data="back_to_users")
        .build()
    )
