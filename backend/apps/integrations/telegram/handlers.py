"""
Telegram Handlers — Process incoming messages and callback queries.
All handlers are synchronous and called from the webhook view.
Heavy work (agent runs) is dispatched to Celery.
"""
import logging
from django.contrib.auth import get_user_model
from django.utils import timezone

logger = logging.getLogger("apps.integrations.telegram")
User = get_user_model()


# ── Command Registry ─────────────────────────────────────────────────────────

COMMANDS = {}


def command(name):
    """Decorator to register a command handler."""
    def decorator(fn):
        COMMANDS[name] = fn
        return fn
    return decorator


# ── Auth Helper ──────────────────────────────────────────────────────────────

def get_user_from_telegram(telegram_user_id: str):
    """Resolve a Telegram user ID to a platform User."""
    return User.objects.filter(
        telegram_user_id=str(telegram_user_id), is_active=True
    ).select_related("company").first()


def handle_update(update: dict):
    """
    Entry point for all incoming Telegram updates.
    Routes to command handlers or callback query handlers.
    """
    if "message" in update:
        _handle_message(update["message"])
    elif "callback_query" in update:
        _handle_callback_query(update["callback_query"])


def _handle_message(message: dict):
    chat_id      = str(message.get("chat", {}).get("id", ""))
    chat_type    = message.get("chat", {}).get("type", "private")
    telegram_user_id = str(message.get("from", {}).get("id", ""))
    text = message.get("text", "").strip()

    if not text:
        return

    # Group/supergroup/channel → try bridge to AIManager chat room
    if chat_type in ("group", "supergroup", "channel"):
        _handle_group_message(chat_id, telegram_user_id, text, message)
        return

    # Private message
    user = get_user_from_telegram(telegram_user_id)
    if not user:
        _send_unregistered_response(chat_id)
        return

    # Parse command vs. natural language
    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0][1:].lower().split("@")[0]  # Strip bot name if present
        args = parts[1] if len(parts) > 1 else ""
        handler = COMMANDS.get(cmd, _handle_unknown_command)
        handler(chat_id, user, args)
    else:
        # Natural language → route to Coordinator Agent
        _handle_natural_language(chat_id, user, text)


def _handle_group_message(chat_id: str, telegram_user_id: str, text: str, raw_message: dict):
    """
    If the Telegram group is linked to an AIManager chat room, save the message
    to the DB and broadcast it to all connected WebSocket clients.
    """
    from apps.chat.models import ChatRoom, ChatMessage

    try:
        room = ChatRoom.objects.select_related("company").get(telegram_chat_id=chat_id)
    except ChatRoom.DoesNotExist:
        return  # Group not linked to any room — ignore silently

    # Try to resolve Telegram user → AIManager user
    user = get_user_from_telegram(telegram_user_id)

    # Build display name from Telegram payload
    from_data = raw_message.get("from", {})
    tg_name = from_data.get("first_name", "")
    if from_data.get("last_name"):
        tg_name += " " + from_data["last_name"]
    if from_data.get("username"):
        tg_name = tg_name or f"@{from_data['username']}"
    tg_name = tg_name.strip() or "Telegram User"

    # Save message to DB
    msg = ChatMessage.objects.create(
        room=room,
        author=user,
        author_display_name="" if user else tg_name,
        body=text,
    )
    ChatRoom.objects.filter(pk=room.pk).update(updated_at=timezone.now())

    # Broadcast via WebSocket channel layer to all connected clients
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        payload = {
            "id":           str(msg.id),
            "room_id":      str(room.id),
            "author_id":    str(user.id) if user else None,
            "author_name":  user.full_name if user else tg_name,
            "author_role":  user.role if user else "telegram",
            "body":         text,
            "created_at":   msg.created_at.isoformat(),
            "related_task":   None,
            "related_report": None,
        }
        async_to_sync(channel_layer.group_send)(
            f"chat_{room.id}",
            {"type": "chat.message", "payload": payload},
        )
    except Exception as exc:
        logger.warning("Failed to broadcast Telegram bridge message via WS: %s", exc)


def _handle_callback_query(callback_query: dict):
    """Handle inline button presses (approval decisions)."""
    callback_id = callback_query.get("id")
    telegram_user_id = str(callback_query.get("from", {}).get("id", ""))
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    message_id = str(message.get("message_id", ""))

    user = get_user_from_telegram(telegram_user_id)
    if not user:
        return

    if ":" not in data:
        return

    action, approval_id = data.split(":", 1)

    if action == "approve":
        _process_approval_decision(user, approval_id, "approved", chat_id, message_id)
    elif action == "reject":
        _process_approval_decision(user, approval_id, "rejected", chat_id, message_id)


def _process_approval_decision(user, approval_id: str, decision: str, chat_id: str, message_id: str):
    from apps.approvals.models import ApprovalRequest
    from django.utils import timezone
    from apps.integrations.telegram.sender import send_message, edit_message_reply_markup

    try:
        approval = ApprovalRequest.objects.get(
            id=approval_id,
            company=user.company,
            status=ApprovalRequest.Status.PENDING,
        )
    except ApprovalRequest.DoesNotExist:
        send_message(chat_id, "This approval request is no longer pending.")
        return

    if not user.can_approve_actions():
        send_message(chat_id, "You don't have permission to approve agent actions.")
        return

    approval.status = (
        ApprovalRequest.Status.APPROVED if decision == "approved"
        else ApprovalRequest.Status.REJECTED
    )
    approval.decided_by = user
    approval.decided_at = timezone.now()
    approval.save()

    # Update the inline keyboard to show the decision
    edit_message_reply_markup(chat_id=chat_id, message_id=message_id)

    icon = "✅" if decision == "approved" else "❌"
    send_message(
        chat_id,
        f"{icon} *{decision.title()}* by {user.first_name}\n\n_{approval.title}_",
    )

    # If approved, execute the action
    if decision == "approved":
        from apps.agents.tasks import run_agent_on_demand
        # Re-trigger agent to execute the approved action
        logger.info("Approval %s approved — executing action", approval_id)


# ── Command Handlers ─────────────────────────────────────────────────────────

@command("start")
def handle_start(chat_id: str, user, args: str):
    from apps.integrations.telegram.sender import send_message
    send_message(
        chat_id,
        f"👋 Hello, *{user.first_name}*!\n\n"
        f"I'm your AIManager assistant for *{user.company.name}*.\n\n"
        f"Available commands:\n"
        f"/status — Company operations snapshot\n"
        f"/tasks — Today's task overview\n"
        f"/blockers — Current blockers\n"
        f"/insights — AI business insights\n"
        f"/ask \\[question\\] — Ask anything\n",
    )


@command("status")
def handle_status(chat_id: str, user, args: str):
    from apps.integrations.telegram.sender import send_message
    from apps.agents.tasks import run_agent_on_demand

    send_message(chat_id, "🔄 Generating operations status...")
    run_agent_on_demand.delay(
        company_id=str(user.company.id),
        agent_type="operations",
        task_description="Give me a concise operations status snapshot: key metrics, overdue tasks, and top 3 priorities for today.",
        user_id=str(user.id),
    )


@command("tasks")
def handle_tasks(chat_id: str, user, args: str):
    from apps.integrations.telegram.sender import send_message
    from apps.tasks.models import Task
    from django.utils import timezone

    tasks = Task.objects.for_company(user.company).filter(
        assigned_to=user,
        status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.BLOCKED],
    ).order_by("due_date")[:10]

    if not tasks:
        send_message(chat_id, "✅ You have no open tasks assigned to you.")
        return

    lines = [f"*Your open tasks ({tasks.count()}):*\n"]
    for t in tasks:
        overdue_flag = " ⚠️ OVERDUE" if t.is_overdue else ""
        due = f" | Due: {t.due_date.strftime('%b %d')}" if t.due_date else ""
        status_icon = {"in_progress": "🔄", "blocked": "🔴", "todo": "⬜"}.get(t.status, "⬜")
        lines.append(f"{status_icon} *{t.title}*{overdue_flag}{due}")

    send_message(chat_id, "\n".join(lines))


@command("blockers")
def handle_blockers(chat_id: str, user, args: str):
    from apps.integrations.telegram.sender import send_message
    from apps.agents.tasks import run_agent_on_demand

    send_message(chat_id, "🔄 Checking for blockers...")
    run_agent_on_demand.delay(
        company_id=str(user.company.id),
        agent_type="operations",
        task_description="List all currently blocked tasks. For each blocker: what's blocking it, who is responsible, and what's the recommended action to unblock it.",
        user_id=str(user.id),
    )


@command("insights")
def handle_insights(chat_id: str, user, args: str):
    from apps.integrations.telegram.sender import send_message
    from apps.agents.tasks import run_agent_on_demand

    send_message(chat_id, "🔄 Generating AI insights...")
    run_agent_on_demand.delay(
        company_id=str(user.company.id),
        agent_type="operations",
        task_description="Generate 3-5 key business insights from current operational data. Focus on trends, risks, and opportunities.",
        user_id=str(user.id),
    )


@command("ask")
def handle_ask(chat_id: str, user, args: str):
    from apps.integrations.telegram.sender import send_message
    from apps.agents.tasks import run_agent_on_demand

    if not args.strip():
        send_message(chat_id, "Usage: /ask [your question]\n\nExample: /ask Which team member has the most overdue tasks?")
        return

    send_message(chat_id, "🤔 Thinking...")
    run_agent_on_demand.delay(
        company_id=str(user.company.id),
        agent_type="operations",
        task_description=args.strip(),
        user_id=str(user.id),
    )


def _handle_natural_language(chat_id: str, user, text: str):
    """Route free-text messages to the Operations Agent."""
    from apps.integrations.telegram.sender import send_message
    from apps.agents.tasks import run_agent_on_demand

    send_message(chat_id, "🤔 Working on it...")
    run_agent_on_demand.delay(
        company_id=str(user.company.id),
        agent_type="operations",
        task_description=text,
        user_id=str(user.id),
    )


def _handle_unknown_command(chat_id: str, user, args: str):
    from apps.integrations.telegram.sender import send_message
    send_message(chat_id, "Unknown command. Type /start to see available commands.")


def _send_unregistered_response(chat_id: str):
    from apps.integrations.telegram.sender import send_message
    send_message(
        chat_id,
        "Your Telegram account is not linked to an AIManager account.\n"
        "Please link your account in the AIManager dashboard under Settings → Telegram.",
    )
