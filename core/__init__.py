import uuid
from dataclasses import dataclass
from telebot.async_telebot import AsyncTeleBot
from telebot.states.asyncio import StateMiddleware

from core.keyboards import InlineKeyboardBuilder, ReplyKeyboardBuilder


@dataclass
class Config:
    flood_waiting: int = 3


class Core:

    def __init__(self, bot: AsyncTeleBot):
        self.bot = bot
        self.config = Config()

    def setup_filters(self):

        from telebot import asyncio_filters
        from .filters import callback_data_filter

        self.bot.add_custom_filter(
            asyncio_filters.StateFilter(self.bot)
        )

        self.bot.add_custom_filter(
            callback_data_filter.F()
        )

    def setup_middlewares(self):

        from .middlewares import flooding

        wait = self.config.flood_waiting

        self.bot.setup_middleware(
            flooding.FloodMiddleware(
                limit=wait,
                bot=self.bot,
                message_text=f"Wait {wait} seconds"
            )
        )


        self.bot.setup_middleware(
            StateMiddleware(self.bot)
        )

    def setup_handler(self):

        from .decorator import make_handler
        from .utils.i18n import I18nEngine
        i18n = I18nEngine()
        return make_handler(
            bot=self.bot,
            i18n=i18n,
            bot_name=str(uuid.uuid4())
        )

    def setup(self):

        self.setup_filters()
        self.setup_middlewares()

        return self.setup_handler()