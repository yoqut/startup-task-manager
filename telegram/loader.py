"""
Bot loader — creates the single AsyncTeleBot instance, wires up all
core infrastructure (filters, middlewares, state storage), and imports
all handler modules so their decorators register against the bot.
"""
from typing import Callable, Any

from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage

import core
from core.config import settings

# ── Bot instance ─────────────────────────────────────────────────────────────
state_storage = StateMemoryStorage()
bot = AsyncTeleBot(
    settings.bot_token,
    state_storage=state_storage,
    parse_mode="HTML",          # default; individual sends can override
)

# ── Core setup (filters + flood middleware + state middleware) ────────────────
core_app = core.Core(bot)
handle: Callable[..., Any] = core_app.setup()

# ── Register bot singleton for notification services ─────────────────────────
from apps.bot.bot import set_bot
set_bot(bot)

from core.sender import Sender
Sender.set_bot(bot)

