"""
Conversation state groups for the Telegram bot.
Each StatesGroup models a distinct multi-step user flow.
"""
from telebot.handler_backends import StatesGroup, State


class RegistrationStates(StatesGroup):
    """User contact sharing during first-time setup."""
    waiting_phone = State()


class TaskCreationStates(StatesGroup):
    """Step-by-step task creation wizard (HEAD / BOSS)."""
    choosing_assign_type = State()    # user vs department
    choosing_department = State()     # pick a department
    choosing_employee = State()       # pick an employee
    entering_title = State()          # task title
    entering_description = State()    # task description
    entering_instructions = State()   # task instructions (skippable)
    choosing_priority = State()       # low / medium / high / urgent
    entering_due_date = State()       # deadline (skippable)
    confirming = State()              # final review & confirm


class ReportSubmitStates(StatesGroup):
    """Report submission flow for employees."""
    choosing_task = State()           # select the task to report on
    entering_text = State()           # report body
    adding_media = State()            # optional photos / files


class ReportReviewStates(StatesGroup):
    """Manager reviews a pending report (accept / reject)."""
    entering_reject_reason = State()  # mandatory rejection comment
    entering_accept_comment = State() # optional acceptance note


class AdminBroadcastStates(StatesGroup):
    """Boss composes and confirms a broadcast message."""
    entering_message = State()
    confirming = State()
