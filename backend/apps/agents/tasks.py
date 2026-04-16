"""
Celery tasks for agent execution.
Scheduled tasks run for every active company.
On-demand tasks run for a specific company.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("apps.agents")


@shared_task(queue="agent_tasks", bind=True, max_retries=2)
def run_operations_agent(self, company_id: str, trigger_source: str = "scheduled", user_id=None):
    """
    Run the Operations Agent for a single company.
    Called on schedule (daily) or on-demand (user command).
    """
    try:
        from apps.tenants.models import Company
        from apps.agents.engine.runner import AgentRunner

        company = Company.objects.get(id=company_id, is_active=True)
        triggered_by = None
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            triggered_by = User.objects.filter(id=user_id).first()

        runner = AgentRunner(
            agent_type="operations",
            company=company,
            task_description=(
                "Perform the daily operations review. "
                "Identify overdue tasks, blocked work, team workload imbalances, "
                "and suggest concrete actions to improve team velocity today."
            ),
            trigger_source=trigger_source,
            triggered_by=triggered_by,
        )
        result = runner.run()
        return {"status": "completed", "log_id": str(result.id) if result else None}

    except Exception as exc:
        logger.exception("run_operations_agent failed for company %s", company_id)
        raise self.retry(exc=exc, countdown=60)


@shared_task(queue="scheduled")
def run_daily_operations_for_all_companies():
    """
    Celery Beat scheduled task — runs every morning for all active companies.
    Each company gets its own task to prevent one failure blocking others.
    """
    from apps.tenants.models import Company

    companies = Company.objects.filter(is_active=True)
    dispatched = 0
    for company in companies:
        run_operations_agent.delay(str(company.id), trigger_source="scheduled")
        dispatched += 1

    logger.info("Dispatched daily operations agent for %d companies", dispatched)
    return {"companies_dispatched": dispatched}


@shared_task(queue="scheduled")
def expire_stale_approvals():
    """
    Mark approval requests past their expiry as 'expired'.
    Runs every hour via Celery Beat.
    """
    from apps.approvals.models import ApprovalRequest

    expired = ApprovalRequest.objects.filter(
        status=ApprovalRequest.Status.PENDING,
        expires_at__lt=timezone.now(),
    )
    count = expired.count()
    expired.update(status=ApprovalRequest.Status.EXPIRED)
    logger.info("Expired %d stale approval requests", count)
    return {"expired": count}


@shared_task(queue="scheduled")
def reset_daily_token_budgets():
    """
    Reset company token counters at midnight UTC.
    Runs daily via Celery Beat.
    """
    from apps.tenants.models import Company

    Company.objects.filter(is_active=True).update(
        tokens_used_today=0,
        tokens_reset_at=timezone.now(),
    )
    logger.info("Reset daily token budgets for all companies")


@shared_task(queue="agent_tasks", bind=True, max_retries=1)
def route_new_task(self, task_id: str, company_id: str):
    """
    Smart task routing: called right after a task is created.
    - Suggests best assignee based on department, role, and current workload.
    - Enriches vague task descriptions with clear objectives.
    - Stores result in task fields and adds an AI comment.
    """
    import json
    from apps.tasks.models import Task, TaskComment
    from apps.agents.engine.client import call_llm, LLMCallError, BudgetExhaustedError
    from apps.tenants.models import Company
    from django.contrib.auth import get_user_model
    from django.db.models import Count

    User = get_user_model()

    try:
        company = Company.objects.get(id=company_id, is_active=True)
        task = Task.objects.select_related("company", "created_by", "assigned_to").get(
            id=task_id, company=company
        )
    except Exception:
        return

    # Get active team members (managers + members, not owners)
    members = User.objects.filter(
        company=company, is_active=True, role__in=["manager", "member"]
    ).select_related("dept")

    if not members.exists():
        return

    # Workload per member (open tasks)
    workload_map = {
        str(row["assigned_to"]): row["cnt"]
        for row in Task.objects.for_company(company)
        .filter(status__in=["todo", "in_progress", "blocked"])
        .exclude(assigned_to__isnull=True)
        .values("assigned_to")
        .annotate(cnt=Count("id"))
    }

    members_data = [
        {
            "id": str(m.id),
            "name": m.full_name,
            "role": m.role,
            "department": m.dept.name if m.dept else "General",
            "open_tasks": workload_map.get(str(m.id), 0),
        }
        for m in members
    ]

    system_prompt = (
        "You are a smart task routing assistant inside a company management system.\n"
        "Given a task and a list of team members, you must:\n"
        "1. Select the most suitable assignee (consider department match, role, "
        "and lowest open_tasks count for balanced workload).\n"
        "2. If the task title/description is vague, write a clear, actionable description "
        "with objectives and success criteria.\n"
        "3. Respond ONLY with valid JSON:\n"
        '{"assignee_id": "<uuid or null>", '
        '"enhanced_description": "<string or null if already clear>", '
        '"priority_score": <0.0-1.0>, '
        '"reasoning": "<1-2 sentence explanation>"}'
    )

    user_msg = (
        f"Task: {task.title}\n"
        f"Description: {task.description or '(none provided)'}\n"
        f"Department: {task.department} | Priority: {task.priority}\n"
        f"Already assigned: {'Yes' if task.assigned_to else 'No'}\n\n"
        f"Team:\n{json.dumps(members_data, ensure_ascii=False, indent=2)}"
    )

    try:
        result = call_llm(
            system_prompt=system_prompt,
            user_message=user_msg,
            company=company,
            max_tokens=500,
            temperature=0.2,
            response_schema=True,
        )
    except (BudgetExhaustedError, LLMCallError) as exc:
        logger.warning("route_new_task: LLM skipped — %s", exc)
        return
    except Exception as exc:
        logger.exception("route_new_task: unexpected error for task %s", task_id)
        raise self.retry(exc=exc, countdown=60)

    data = result.parsed
    if not isinstance(data, dict):
        return

    updates = {}
    if data.get("priority_score") is not None:
        updates["ai_priority_score"] = float(data["priority_score"])

    assignee = None
    assignee_id = data.get("assignee_id")
    if assignee_id:
        try:
            assignee = User.objects.get(id=assignee_id, company=company)
            updates["ai_suggested_assignee"] = assignee
            if not task.assigned_to:          # auto-assign only when unassigned
                updates["assigned_to"] = assignee
        except User.DoesNotExist:
            pass

    if updates:
        Task.objects.filter(id=task_id).update(**updates)

    # Add AI analysis as a pinned comment
    parts = []
    enhanced = (data.get("enhanced_description") or "").strip()
    reasoning = (data.get("reasoning") or "").strip()

    if enhanced and enhanced.lower() != (task.description or "").lower():
        parts.append(f"**Tavsif:**\n{enhanced}")
    if assignee and not task.assigned_to:
        parts.append(f"**Tavsiya etilgan ijrochi:** {assignee.full_name}")
    if reasoning:
        parts.append(f"**Tayinlash asosi:** {reasoning}")

    if parts:
        TaskComment.objects.create(
            task_id=task_id,
            body="🤖 **AI Tahlili**\n\n" + "\n\n".join(parts),
            is_ai_generated=True,
        )

    logger.info("Task routed | task=%s | assignee=%s | score=%.2f",
                task_id, assignee_id, data.get("priority_score", 0))


@shared_task(queue="agent_tasks", bind=True, max_retries=1)
def monitor_chat_room(self, room_id: str, company_id: str):
    """
    Triggered every ~10 messages in a monitored chat room.
    Scans recent messages for actionable items: blocked tasks mentioned,
    decisions made, or requests that should become tasks.
    """
    try:
        from apps.chat.models import ChatRoom
        from apps.tenants.models import Company
        from apps.agents.engine.client import call_llm, LLMCallError, BudgetExhaustedError

        company = Company.objects.get(id=company_id, is_active=True)
        room = ChatRoom.objects.select_related("company").get(id=room_id, company=company)

        # Get last 20 messages
        messages = list(
            room.messages.select_related("author").order_by("-created_at")[:20]
        )
        if not messages:
            return

        messages.reverse()
        chat_text = "\n".join(
            f"[{m.author.full_name if m.author else 'Unknown'}]: {m.body}"
            for m in messages
        )

        system_prompt = (
            "You are an operations assistant monitoring a team chat room.\n"
            "Analyze the recent messages and identify:\n"
            "1. Any tasks or action items that should be tracked\n"
            "2. Blocked work or problems that need attention\n"
            "3. Decisions that were made\n"
            "If nothing actionable is found, return {\"actions\": []}.\n"
            "Return JSON: {\"actions\": [{\"type\": \"create_task|alert\", "
            "\"title\": \"...\", \"description\": \"...\", \"priority\": \"medium\"}]}"
        )

        result = call_llm(
            system_prompt=system_prompt,
            user_message=f"Chat room: {room.name}\n\nRecent messages:\n{chat_text}",
            company=company,
            max_tokens=400,
            temperature=0.2,
            response_schema=True,
        )

        actions = result.parsed.get("actions", [])
        for action_item in actions:
            if action_item.get("type") == "create_task" and action_item.get("title"):
                from apps.tasks.models import Task
                Task.objects.create(
                    company=company,
                    title=action_item["title"][:500],
                    description=action_item.get("description", ""),
                    priority=action_item.get("priority", "medium"),
                    department="general",
                    status="todo",
                    is_ai_created=True,
                )
                logger.info("Chat monitor created task: %s", action_item["title"])

    except (LLMCallError, BudgetExhaustedError):
        pass  # Budget issues are non-fatal for monitoring
    except Exception as exc:
        logger.exception("monitor_chat_room failed | room=%s", room_id)
        raise self.retry(exc=exc, countdown=120)


@shared_task(queue="agent_tasks", bind=True, max_retries=2)
def run_agent_on_demand(self, company_id: str, agent_type: str, task_description: str, user_id=None):
    """
    Generic on-demand agent runner triggered by user commands (dashboard or Telegram).
    """
    try:
        from apps.tenants.models import Company
        from apps.agents.engine.runner import AgentRunner

        company = Company.objects.get(id=company_id, is_active=True)
        triggered_by = None
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            triggered_by = User.objects.filter(id=user_id).first()

        runner = AgentRunner(
            agent_type=agent_type,
            company=company,
            task_description=task_description,
            trigger_source="user_command",
            triggered_by=triggered_by,
        )
        result = runner.run()
        return {"status": "completed", "log_id": str(result.id) if result else None}

    except Exception as exc:
        logger.exception("run_agent_on_demand failed | company=%s | agent=%s", company_id, agent_type)
        raise self.retry(exc=exc, countdown=30)
