from typing import Callable, Any
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage

import core
from core.config import settings

state_storage = StateMemoryStorage()

bot = AsyncTeleBot(settings.bot_token, state_storage=state_storage)

core_app = core.Core(bot)
handle: Callable[..., Any] = core_app.setup()

# handlerlarni yuklash
import telegram.handlers