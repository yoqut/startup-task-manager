"""
Telegram Sender — Low-level API wrapper for sending messages and building keyboards.
Uses requests (sync) called from Celery workers.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger("apps.integrations.telegram")

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"


def _api_call(method: str, payload: dict) -> dict:
    url = TELEGRAM_API_BASE.format(token=settings.TELEGRAM_BOT_TOKEN, method=method)
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise ValueError(f"Telegram API error: {data.get('description')}")
        return data.get("result", {})
    except Exception as e:
        logger.error("Telegram API call failed | method=%s | error=%s", method, e)
        raise


def send_message(chat_id: str, text: str, parse_mode: str = "Markdown", reply_markup: dict = None) -> dict:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _api_call("sendMessage", payload)


def send_approval_message(chat_id: str, approval) -> dict:
    """
    Send an approval request with inline approve/reject buttons.
    """
    confidence_pct = int((approval.confidence_score or 0) * 100)
    agent_display = approval.agent_type.replace("_", " ").title()

    text = (
        f"*{agent_display} — Action Required*\n\n"
        f"*Action:* {approval.title}\n\n"
        f"*Reasoning:*\n{approval.reasoning[:400]}\n\n"
        f"*Confidence:* {confidence_pct}%\n"
        f"*Expires:* {approval.expires_at.strftime('%b %d, %H:%M UTC')}"
    )

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"approve:{approval.id}"},
                {"text": "❌ Reject", "callback_data": f"reject:{approval.id}"},
            ]
        ]
    }

    return send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


def edit_message_reply_markup(chat_id: str, message_id: str, reply_markup: dict = None) -> dict:
    """Remove or update inline keyboard after a decision is made."""
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": reply_markup or {"inline_keyboard": []},
    }
    return _api_call("editMessageReplyMarkup", payload)


def set_webhook(webhook_url: str, secret_token: str) -> dict:
    payload = {
        "url": webhook_url,
        "secret_token": secret_token,
        "allowed_updates": ["message", "callback_query"],
    }
    return _api_call("setWebhook", payload)
