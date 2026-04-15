"""
Task management handlers.

Employee
  • View their own tasks (paginated, filterable)
  • View task detail with status-change inline buttons

HEAD / BOSS
  • All of the above for all / department tasks
  • Multi-step task-creation wizard (fully inline)
"""
import logging
from datetime import datetime

from telegram.loader import bot, handle
from core.sender import Sender
from telegram.keyboards.inlines import (
    task_list_inl, task_filter_inl, task_detail_inl,
    task_status_cb, task_cb, page_cb,
    assign_type_inl, departments_inl, employees_inl,
    priority_inl, confirm_task_inl,
    get_main_menu,
    wizard_cancel_inl, wizard_skip_cancel_inl,
)
from telegram.states import TaskCreationStates
from apps.users.models import UserRole

logger = logging.getLogger("telegram.handlers")

# ---------------------------------------------------------------------------
# Shared helper — show task list
# ---------------------------------------------------------------------------

async def show_task_list(
    chat_id: int,
    user_id: int,
    db_user,
    page: int = 0,
    filter_key: str = "all",
    edit_message_id: int | None = None,
):
    from apps.tasks.services import aget_user_tasks, aget_all_tasks, aget_department_tasks
    from apps.tasks.models import TaskStatus

    status_map = {
        "new": TaskStatus.NEW, "in_progress": TaskStatus.IN_PROGRESS,
        "completed": TaskStatus.COMPLETED, "overdue": TaskStatus.OVERDUE,
    }
    status_filter = status_map.get(filter_key) if filter_key != "all" else None

    if db_user.role == UserRole.BOSS:
        tasks = await aget_all_tasks(status_filter=status_filter)
        title = "📋 Barcha vazifalar"
    elif db_user.role == UserRole.HEAD and db_user.department_id:
        tasks = await aget_department_tasks(db_user.department_id, status_filter=status_filter)
        title = "📋 Bo'lim vazifalari"
    else:
        tasks = await aget_user_tasks(db_user, status_filter)
        title = "📋 Mening vazifalarim"

    if not tasks:
        text = f"{title}\n\n📭 Vazifalar topilmadi."
        if edit_message_id:
            await Sender.edit_html(chat_id, edit_message_id, text)
        else:
            await Sender.send_html(chat_id, text)
        return

    page_items, total_pages, page = Sender.paginate(tasks, page)
    markup = task_list_inl(page_items, page, total_pages, filter_key)
    text   = f"{title} ({len(tasks)} ta)"
    if edit_message_id:
        await Sender.edit_html(chat_id, edit_message_id, text, markup)
    else:
        await Sender.send_html(chat_id, text, markup)


# ---------------------------------------------------------------------------
# Task-creation entry point  (called from commands.py menu dispatcher)
# ---------------------------------------------------------------------------

async def _start_new_task(chat_id: int, user_id: int, user):
    """Begin the task-creation wizard."""
    await bot.set_state(user_id, TaskCreationStates.choosing_assign_type, chat_id)
    async with bot.retrieve_data(user_id, chat_id) as data:
        data.clear()
        data["creator_id"] = user.id
    await Sender.send_html(
        chat_id,
        "📝 <b>Yangi vazifa yaratish</b>\n\nVazifani kimga tayinlaysiz?",
        markup=assign_type_inl(),
    )


# ---------------------------------------------------------------------------
# Task-list callbacks — pagination & filter
# ---------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda c: c.data.startswith("pg:tasks:"))
async def cb_task_page(call):
    await bot.answer_callback_query(call.id)
    try:
        parsed     = page_cb.parse(call.data)
        page       = int(parsed["page"])
        filter_key = parsed["flt"]
    except Exception:
        return
    user = await Sender.get_db_user(call.from_user.id)
    if not user:
        return
    result = await _build_task_list_message(call.from_user.id, user, page, filter_key)
    if result:
        items, total_pages, page = result
        await Sender.edit_html(
            call.message.chat.id, call.message.message_id,
            f"📋 Vazifalar ({filter_key})",
            markup=task_list_inl(items, page, total_pages, filter_key),
        )


@bot.callback_query_handler(func=lambda c: c.data.startswith("tasks_filter:"))
async def cb_task_filter(call):
    await bot.answer_callback_query(call.id)
    current = call.data.split(":")[1]
    await Sender.edit_html(
        call.message.chat.id, call.message.message_id,
        "🔍 Filterni tanlang:",
        markup=task_filter_inl(current),
    )


@bot.callback_query_handler(func=lambda c: c.data == "back_to_tasks")
async def cb_back_to_tasks(call):
    await bot.answer_callback_query(call.id)
    user = await Sender.get_db_user(call.from_user.id)
    if user:
        await show_task_list(call.message.chat.id, call.from_user.id, user)


# ---------------------------------------------------------------------------
# Task detail view
# ---------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda c: c.data.startswith("task:") and ":view:" in c.data)
async def cb_task_view(call):
    await bot.answer_callback_query(call.id)
    try:
        task_id = int(task_cb.parse(call.data)["task_id"])
    except Exception:
        return

    user = await Sender.get_db_user(call.from_user.id)
    if not user:
        return

    from apps.tasks.services import aget_task_instance
    task = await aget_task_instance(task_id)
    if not task:
        await Sender.send_html(call.message.chat.id, "❌ Vazifa topilmadi.")
        return

    if user.role == UserRole.EMPLOYEE and task.assigned_user_id != user.id:
        await Sender.send_html(call.message.chat.id, "❌ Bu vazifani ko'rish uchun ruxsatingiz yo'q.")
        return

    text   = Sender.format_task(task, show_instructions=True)
    markup = task_detail_inl(task, user.role)
    await Sender.edit_html(call.message.chat.id, call.message.message_id, text, markup=markup)


# ---------------------------------------------------------------------------
# Task status change
# ---------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda c: c.data.startswith("tstatus:"))
async def cb_task_status(call):
    await bot.answer_callback_query(call.id)
    try:
        parsed     = task_status_cb.parse(call.data)
        task_id    = int(parsed["task_id"])
        new_status = parsed["status"]
    except Exception:
        return

    user = await Sender.get_db_user(call.from_user.id)
    if not user:
        return

    from apps.tasks.services import aget_task_instance, achange_task_status
    task = await aget_task_instance(task_id)
    if not task:
        await Sender.send_html(call.message.chat.id, "❌ Vazifa topilmadi.")
        return

    try:
        task = await achange_task_status(task, new_status, user)
        from apps.tasks.models import TaskStatus
        status_label = TaskStatus(new_status).label
        await bot.answer_callback_query(call.id, f"✅ Holat: {status_label}", show_alert=True)
        await Sender.edit_html(
            call.message.chat.id, call.message.message_id,
            Sender.format_task(task, show_instructions=True),
            markup=task_detail_inl(task, user.role),
        )
    except (ValueError, PermissionError) as exc:
        await bot.answer_callback_query(call.id, f"❌ {exc}", show_alert=True)
    except Exception as exc:
        logger.error("Task status change error: %s", exc)
        await bot.answer_callback_query(call.id, "❌ Xatolik yuz berdi.", show_alert=True)


# ---------------------------------------------------------------------------
# Task creation wizard
# ---------------------------------------------------------------------------

# -- step 1: assign type --

@bot.callback_query_handler(func=lambda c: c.data in ("assign:user", "assign:department"))
async def cb_assign_type(call):
    await bot.answer_callback_query(call.id)
    if await bot.get_state(call.from_user.id, call.message.chat.id) != TaskCreationStates.choosing_assign_type.name:
        return

    assign_type = call.data.split(":")[1]
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data["assign_type"] = assign_type

    if assign_type == "department":
        from apps.departments.services import aget_all_active_departments
        departments = await aget_all_active_departments()
        if not departments:
            await Sender.send_html(call.message.chat.id, "❌ Faol bo'limlar topilmadi.")
            await bot.delete_state(call.from_user.id, call.message.chat.id)
            return
        await bot.set_state(call.from_user.id, TaskCreationStates.choosing_department, call.message.chat.id)
        await Sender.edit_html(call.message.chat.id, call.message.message_id, "🏢 Bo'limni tanlang:", markup=departments_inl(departments))
    else:
        user = await Sender.get_db_user(call.from_user.id)
        if user.role == UserRole.HEAD and user.department_id:
            from apps.users.services import aget_department_employees
            employees = await aget_department_employees(user.department_id)
        else:
            from apps.users.services import aget_all_active_employees
            employees = await aget_all_active_employees()

        if not employees:
            await Sender.send_html(call.message.chat.id, "❌ Faol xodimlar topilmadi.")
            await bot.delete_state(call.from_user.id, call.message.chat.id)
            return
        await bot.set_state(call.from_user.id, TaskCreationStates.choosing_employee, call.message.chat.id)
        await Sender.edit_html(call.message.chat.id, call.message.message_id, "👤 Xodimni tanlang:", markup=employees_inl(employees))


# -- step 2a: department selected --

@bot.callback_query_handler(func=lambda c: c.data.startswith("dept:"))
async def cb_dept_selected(call):
    await bot.answer_callback_query(call.id)
    if await bot.get_state(call.from_user.id, call.message.chat.id) != TaskCreationStates.choosing_department.name:
        return

    dept_id = int(call.data.split(":")[1])
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data["assigned_department_id"] = dept_id
        data["assigned_user_id"] = None

    await bot.set_state(call.from_user.id, TaskCreationStates.entering_title, call.message.chat.id)
    await Sender.edit_html(call.message.chat.id, call.message.message_id, "📝 Vazifa sarlavhasini kiriting:")
    await Sender.send_html(
        call.message.chat.id, "✏️ Sarlavha yozing:",
        markup=wizard_cancel_inl("cancel_task_creation"),
    )


# -- step 2b: employee selected --

@bot.callback_query_handler(func=lambda c: c.data.startswith("emp:"))
async def cb_emp_selected(call):
    await bot.answer_callback_query(call.id)
    if await bot.get_state(call.from_user.id, call.message.chat.id) != TaskCreationStates.choosing_employee.name:
        return

    emp_id = int(call.data.split(":")[1])
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data["assigned_user_id"] = emp_id
        data["assigned_department_id"] = None

    await bot.set_state(call.from_user.id, TaskCreationStates.entering_title, call.message.chat.id)
    await Sender.edit_html(call.message.chat.id, call.message.message_id, "📝 Sarlavha kiriting:")
    await Sender.send_html(
        call.message.chat.id, "✏️ Sarlavha yozing:",
        markup=wizard_cancel_inl("cancel_task_creation"),
    )


# -- step 3: title (text input) --

@handle(state=TaskCreationStates.entering_title)
async def state_task_title(sender):
    text = (sender.msg.text or "").strip()
    if not text:
        return
    if len(text) > 500:
        await Sender.send_html(sender.chat_id, "❌ Sarlavha 500 belgidan oshmasligi kerak. Qaytadan:",
                        markup=wizard_cancel_inl("cancel_task_creation"))
        return
    async with bot.retrieve_data(sender.user_id, sender.chat_id) as data:
        data["title"] = text
    await bot.set_state(sender.user_id, TaskCreationStates.entering_description, sender.chat_id)
    await Sender.send_html(sender.chat_id, "📄 Vazifa tavsifini kiriting:",
                    markup=wizard_cancel_inl("cancel_task_creation"))


# -- step 4: description (text input) --

@handle(state=TaskCreationStates.entering_description)
async def state_task_desc(sender):
    text = (sender.msg.text or "").strip()
    if not text:
        return
    async with bot.retrieve_data(sender.user_id, sender.chat_id) as data:
        data["description"] = text
    await bot.set_state(sender.user_id, TaskCreationStates.entering_instructions, sender.chat_id)
    await Sender.send_html(
        sender.chat_id,
        "📋 Ko'rsatmalar kiriting (ixtiyoriy):",
        markup=wizard_skip_cancel_inl("task_wizard:skip_instructions", "cancel_task_creation"),
    )


# -- step 5: instructions (text input, skippable) --

@handle(state=TaskCreationStates.entering_instructions)
async def state_task_instructions(sender):
    text = (sender.msg.text or "").strip()
    if not text:
        return
    async with bot.retrieve_data(sender.user_id, sender.chat_id) as data:
        data["instructions"] = text
    await bot.set_state(sender.user_id, TaskCreationStates.choosing_priority, sender.chat_id)
    await Sender.send_html(sender.chat_id, "⚡ Ustuvorlikni tanlang:", markup=priority_inl())


@bot.callback_query_handler(func=lambda c: c.data == "task_wizard:skip_instructions")
async def cb_skip_instructions(call):
    await bot.answer_callback_query(call.id)
    if await bot.get_state(call.from_user.id, call.message.chat.id) != TaskCreationStates.entering_instructions.name:
        return
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data["instructions"] = ""
    await bot.set_state(call.from_user.id, TaskCreationStates.choosing_priority, call.message.chat.id)
    await Sender.edit_html(call.message.chat.id, call.message.message_id, "⚡ Ustuvorlikni tanlang:", markup=priority_inl())


# -- step 6: priority (inline button) --

@bot.callback_query_handler(func=lambda c: c.data.startswith("priority:"))
async def cb_priority_selected(call):
    await bot.answer_callback_query(call.id)
    if await bot.get_state(call.from_user.id, call.message.chat.id) != TaskCreationStates.choosing_priority.name:
        return

    priority = call.data.split(":")[1]
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data["priority"] = priority

    await bot.set_state(call.from_user.id, TaskCreationStates.entering_due_date, call.message.chat.id)
    await Sender.edit_html(
        call.message.chat.id, call.message.message_id,
        "📅 Muddat kiriting (kk.oo.yyyy ss:mm)\nMasalan: <code>25.12.2025 18:00</code>",
    )
    await Sender.send_html(
        call.message.chat.id, "📅 Muddat (yoki o'tkazib yuboring):",
        markup=wizard_skip_cancel_inl("task_wizard:skip_due_date", "cancel_task_creation"),
    )


# -- step 7: due date (text input, skippable) --

@handle(state=TaskCreationStates.entering_due_date)
async def state_task_due_date(sender):
    text = (sender.msg.text or "").strip()
    if not text:
        return
    try:
        due_at = datetime.strptime(text, "%d.%m.%Y %H:%M")
    except ValueError:
        await Sender.send_html(
            sender.chat_id,
            "❌ Sana noto'g'ri formatda. Qaytadan (kk.oo.yyyy ss:mm):",
            markup=wizard_skip_cancel_inl("task_wizard:skip_due_date", "cancel_task_creation"),
        )
        return
    await _proceed_to_confirm(sender.user_id, sender.chat_id, due_at)


@bot.callback_query_handler(func=lambda c: c.data == "task_wizard:skip_due_date")
async def cb_skip_due_date(call):
    await bot.answer_callback_query(call.id)
    if await bot.get_state(call.from_user.id, call.message.chat.id) != TaskCreationStates.entering_due_date.name:
        return
    await _proceed_to_confirm(call.from_user.id, call.message.chat.id, due_at=None, edit_msg=call.message)


async def _proceed_to_confirm(user_id: int, chat_id: int, due_at, edit_msg=None):
    """Build confirm preview and advance wizard to confirming state."""
    async with bot.retrieve_data(user_id, chat_id) as data:
        data["due_at"] = due_at.isoformat() if due_at else None
        title       = data.get("title", "")
        description = data.get("description", "")
        priority    = data.get("priority", "medium")

    prio_labels = {
        "low": "⬇️ Past", "medium": "➡️ O'rta",
        "high": "⬆️ Yuqori", "urgent": "🚨 Shoshilinch",
    }
    due_str = due_at.strftime("%d.%m.%Y %H:%M") if due_at else "Ko'rsatilmagan"
    confirm_text = (
        f"✅ <b>Vazifani tasdiqlaysizmi?</b>\n\n"
        f"📌 Sarlavha: <b>{title}</b>\n"
        f"📄 Tavsif: {description[:200]}\n"
        f"⚡ Ustuvorlik: {prio_labels.get(priority, priority)}\n"
        f"📅 Muddat: {due_str}"
    )
    await bot.set_state(user_id, TaskCreationStates.confirming, chat_id)
    if edit_msg:
        await Sender.edit_html(chat_id, edit_msg.message_id, confirm_text, markup=confirm_task_inl())
    else:
        await Sender.send_html(chat_id, confirm_text, markup=confirm_task_inl())


# -- step 8: confirm --

@bot.callback_query_handler(func=lambda c: c.data in ("confirm:yes:task", "confirm:no:task"))
async def cb_task_confirm(call):
    await bot.answer_callback_query(call.id)
    if await bot.get_state(call.from_user.id, call.message.chat.id) != TaskCreationStates.confirming.name:
        return

    if call.data == "confirm:no:task":
        await bot.delete_state(call.from_user.id, call.message.chat.id)
        user = await Sender.get_db_user(call.from_user.id)
        await Sender.edit_html(call.message.chat.id, call.message.message_id,
                        "❌ Bekor qilindi.", markup=get_main_menu(user))
        return

    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        task_data = dict(data)

    await bot.delete_state(call.from_user.id, call.message.chat.id)

    try:
        creator = await Sender.get_db_user(call.from_user.id)
        due_at  = datetime.fromisoformat(task_data["due_at"]) if task_data.get("due_at") else None

        assigned_user       = None
        assigned_department = None

        if task_data.get("assigned_user_id"):
            from asgiref.sync import sync_to_async
            from apps.users.models import User
            assigned_user = await sync_to_async(
                lambda: User.objects.filter(id=task_data["assigned_user_id"]).first()
            )()
        if task_data.get("assigned_department_id"):
            from asgiref.sync import sync_to_async
            from apps.departments.models import Department
            assigned_department = await sync_to_async(
                lambda: Department.objects.filter(id=task_data["assigned_department_id"]).first()
            )()

        from apps.tasks.services import acreate_one_time_task
        instances = await acreate_one_time_task(
            creator=creator,
            title=task_data["title"],
            description=task_data.get("description", ""),
            instructions=task_data.get("instructions", ""),
            priority=task_data.get("priority", "medium"),
            due_at=due_at,
            assigned_user=assigned_user,
            assigned_department=assigned_department,
        )

        from apps.notifications.services import anotify_task_assigned
        import asyncio
        await asyncio.gather(*[
            anotify_task_assigned(inst, inst.assigned_user)
            for inst in instances if inst.assigned_user
        ])

        user = await Sender.get_db_user(call.from_user.id)
        await Sender.edit_html(
            call.message.chat.id, call.message.message_id,
            f"✅ Vazifa muvaffaqiyatli yaratildi! ({len(instances)} ta tayinlandi)",
            markup=get_main_menu(user),
        )

    except (ValueError, PermissionError) as exc:
        user = await Sender.get_db_user(call.from_user.id)
        await Sender.send_html(call.message.chat.id, f"❌ Xatolik: {exc}", markup=get_main_menu(user))
    except Exception as exc:
        logger.error("Task creation failed: %s", exc)
        await Sender.send_html(call.message.chat.id, "❌ Vazifa yaratishda xatolik yuz berdi.")


# -- cancel callback --

@bot.callback_query_handler(func=lambda c: c.data == "cancel_task_creation")
async def cb_cancel_task_creation(call):
    await bot.answer_callback_query(call.id)
    await bot.delete_state(call.from_user.id, call.message.chat.id)
    user = await Sender.get_db_user(call.from_user.id)
    await Sender.edit_html(call.message.chat.id, call.message.message_id,
                    "❌ Bekor qilindi.", markup=get_main_menu(user))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _build_task_list_message(user_id, db_user, page, filter_key):
    from apps.tasks.services import aget_user_tasks, aget_all_tasks, aget_department_tasks
    from apps.tasks.models import TaskStatus

    status_map = {
        "new": TaskStatus.NEW, "in_progress": TaskStatus.IN_PROGRESS,
        "completed": TaskStatus.COMPLETED, "overdue": TaskStatus.OVERDUE,
    }
    status_filter = status_map.get(filter_key) if filter_key != "all" else None

    if db_user.role == UserRole.BOSS:
        tasks = await aget_all_tasks(status_filter=status_filter)
    elif db_user.role == UserRole.HEAD and db_user.department_id:
        tasks = await aget_department_tasks(db_user.department_id, status_filter=status_filter)
    else:
        tasks = await aget_user_tasks(db_user, status_filter)

    if not tasks:
        return None
    return Sender.paginate(tasks, page)
