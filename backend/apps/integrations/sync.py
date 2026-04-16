"""
CRM/ERP Sync Engine
Handles both inbound (CRM → AIManager) and outbound (AIManager → CRM) sync.
Each integration type has its own translator that maps fields to/from Task model.
"""
import logging
import requests
from django.utils import timezone

logger = logging.getLogger("apps.integrations")


# ── Inbound: CRM → AIManager ──────────────────────────────────────────────────

def process_inbound_payload(integration, payload: dict) -> dict:
    """
    Translate a CRM webhook payload into an AIManager task (create or update).
    Returns {"created": N, "updated": N, "skipped": N}.
    """
    translators = {
        "bitrix24": _translate_bitrix24,
        "amocrm":   _translate_amocrm,
        "odoo":     _translate_odoo,
        "generic":  _translate_generic,
    }
    translator = translators.get(integration.type, _translate_generic)
    task_data  = translator(payload, integration.config)

    if not task_data:
        return {"created": 0, "updated": 0, "skipped": 1}

    from apps.tasks.models import Task

    external_id   = task_data.pop("external_id", None)
    external_type = integration.type

    # Try to find existing task by external ref
    existing = None
    if external_id:
        existing = Task.objects.for_company(integration.company).filter(
            external_ref_type=external_type,
            external_ref_id=str(external_id),
        ).first()

    if existing:
        for field, value in task_data.items():
            setattr(existing, field, value)
        existing.save()
        return {"created": 0, "updated": 1, "skipped": 0}
    else:
        Task.objects.create(
            company=integration.company,
            external_ref_type=external_type,
            external_ref_id=str(external_id) if external_id else "",
            is_ai_created=False,
            **task_data,
        )
        return {"created": 1, "updated": 0, "skipped": 0}


# ── Outbound: AIManager → CRM ─────────────────────────────────────────────────

def push_task_to_crm(integration, task) -> bool:
    """
    Push a task status/update to the external CRM/ERP.
    Returns True on success.
    """
    if not integration.is_active or integration.sync_direction == "import":
        return False
    if not integration.api_url:
        return False

    pushers = {
        "bitrix24": _push_bitrix24,
        "amocrm":   _push_amocrm,
        "odoo":     _push_odoo,
        "generic":  _push_generic,
    }
    pusher = pushers.get(integration.type, _push_generic)
    try:
        pusher(integration, task)
        return True
    except Exception as exc:
        logger.error("CRM push failed | integration=%s | error=%s", integration.id, exc)
        integration.last_error = str(exc)
        integration.save(update_fields=["last_error"])
        return False


# ── Field Translators ─────────────────────────────────────────────────────────

def _translate_bitrix24(payload: dict, config: dict) -> dict | None:
    """Bitrix24 task webhook → AIManager Task fields."""
    data = payload.get("data", {}).get("FIELDS", payload)
    if not data.get("TITLE"):
        return None
    status_map = {
        "2": "todo", "3": "in_progress", "4": "in_review",
        "5": "done", "6": "blocked", "7": "cancelled",
    }
    return {
        "title":       data.get("TITLE", "Untitled"),
        "description": data.get("DESCRIPTION", ""),
        "status":      status_map.get(str(data.get("STATUS")), "todo"),
        "priority":    "high" if str(data.get("PRIORITY")) == "2" else "medium",
        "external_id": data.get("ID"),
    }


def _translate_amocrm(payload: dict, config: dict) -> dict | None:
    """AmoCRM lead/task webhook → AIManager Task fields."""
    lead = (payload.get("leads", {}).get("add") or [None])[0]
    if not lead:
        lead = payload
    if not lead.get("name"):
        return None
    return {
        "title":       lead.get("name", "Untitled"),
        "description": lead.get("custom_fields_values", [{}])[0].get("values", [{}])[0].get("value", ""),
        "status":      "todo",
        "priority":    "medium",
        "department":  "sales",
        "external_id": lead.get("id"),
    }


def _translate_odoo(payload: dict, config: dict) -> dict | None:
    """Odoo project.task → AIManager Task fields."""
    if not payload.get("name"):
        return None
    stage_map = {
        "New": "todo", "In Progress": "in_progress",
        "Done": "done", "Cancelled": "cancelled",
    }
    return {
        "title":       payload.get("name", "Untitled"),
        "description": payload.get("description", ""),
        "status":      stage_map.get(payload.get("stage", "New"), "todo"),
        "priority":    "high" if payload.get("priority") == "1" else "medium",
        "external_id": payload.get("id"),
    }


def _translate_generic(payload: dict, config: dict) -> dict | None:
    """Generic webhook: expects AIManager-like field names."""
    if not payload.get("title"):
        return None
    return {
        "title":       payload.get("title", "Untitled"),
        "description": payload.get("description", ""),
        "status":      payload.get("status", "todo"),
        "priority":    payload.get("priority", "medium"),
        "department":  payload.get("department", "general"),
        "external_id": payload.get("id") or payload.get("external_id"),
    }


# ── Push Helpers ──────────────────────────────────────────────────────────────

def _push_generic(integration, task):
    endpoint = integration.config.get("task_update_endpoint", "/tasks/{id}")
    url = integration.api_url.rstrip("/") + endpoint.replace("{id}", task.external_ref_id or "")
    headers = {"Authorization": f"Bearer {integration.api_key}"} if integration.api_key else {}
    payload = {
        "id":          task.external_ref_id,
        "title":       task.title,
        "status":      task.status,
        "priority":    task.priority,
        "description": task.description,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()


def _push_bitrix24(integration, task):
    if not task.external_ref_id:
        return
    status_map = {"todo": "2", "in_progress": "3", "in_review": "4",
                  "done": "5", "blocked": "6", "cancelled": "7"}
    url = f"{integration.api_url.rstrip('/')}/tasks.task.update.json"
    params = {"taskId": task.external_ref_id, "fields[STATUS]": status_map.get(task.status, "2")}
    headers = {"Authorization": f"Bearer {integration.api_key}"} if integration.api_key else {}
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    resp.raise_for_status()


def _push_amocrm(integration, task):
    if not task.external_ref_id:
        return
    url = f"{integration.api_url.rstrip('/')}/api/v4/leads/{task.external_ref_id}"
    headers = {"Authorization": f"Bearer {integration.api_key}"}
    payload = [{"id": int(task.external_ref_id), "name": task.title}]
    resp = requests.patch(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()


def _push_odoo(integration, task):
    """Odoo JSON-RPC update."""
    if not task.external_ref_id:
        return
    url = f"{integration.api_url.rstrip('/')}/web/dataset/call_kw"
    payload = {
        "jsonrpc": "2.0", "method": "call", "id": 1,
        "params": {
            "model": "project.task",
            "method": "write",
            "args": [[int(task.external_ref_id)], {"name": task.title}],
            "kwargs": {},
        },
    }
    headers = {"Content-Type": "application/json"}
    if integration.api_key:
        headers["Cookie"] = f"session_id={integration.api_key}"
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
