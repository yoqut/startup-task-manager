"""
Global bot singleton — lets service-layer code (notifications, Celery tasks, etc.)
send Telegram messages without importing from the telegram/ app layer.

Usage:
    # In telegram/loader.py (startup):
    from apps.bot.bot import set_bot
    set_bot(bot_instance)

    # In any service:
    from apps.bot.bot import get_bot
    bot = get_bot()
    if bot:
        await bot.send_message(telegram_id, text)
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telebot.async_telebot import AsyncTeleBot

logger = logging.getLogger("apps.bot")

_bot_instance: "AsyncTeleBot | None" = None


def set_bot(bot: "AsyncTeleBot") -> None:
    global _bot_instance
    _bot_instance = bot
    logger.info("Bot singleton registered.")


def get_bot() -> "AsyncTeleBot | None":
    if _bot_instance is None:
        logger.warning("Bot singleton accessed before set_bot() was called.")
    return _bot_instance
