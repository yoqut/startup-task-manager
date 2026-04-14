from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeAlias

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, CallbackQuery

from .sender import Sender

logger = logging.getLogger(__name__)

MessageLike: TypeAlias = Message | CallbackQuery
_DEFAULT_CB_FILTER: Callable[[CallbackQuery], bool] = lambda _: True
msg_type = False

def make_handler(bot: AsyncTeleBot, i18n, bot_name: str = 'bot'):

    def handler(*, func: Callable[[Any], bool] | None = None, **decorator_kwargs: Any) -> Callable:
        """
        Decorator factory.

        Parameters
        ----------
        func            : optional additional filter predicate
        decorator_kwargs: passed directly to bot.message_handler / bot.callback_query_handler
        """
        global msg_type
        def decorator(handler_func: Callable) -> Callable:

            @wraps(handler_func)
            async def wrapper(msg: MessageLike, *args: Any, **kwargs: Any) -> None:
                try:
                    global msg_type

                    if isinstance(msg, CallbackQuery):
                        msg_type = "callback"
                    if isinstance(msg, Message):
                        msg_type = "message"
                    else:
                        msg_type = "middleware"


                    sender = Sender(bot, msg, i18n)

                    await handler_func(sender, *args, **kwargs)

                except Exception as ex:
                    logger.exception(
                        "[%s] Unhandled error %s in handler %s",
                        bot_name,
                        ex,
                        handler_func.__qualname__,
                    )

            if msg_type == "callback":
                bot.callback_query_handler(func=func or _DEFAULT_CB_FILTER, **decorator_kwargs)(wrapper)
            elif msg_type == "message":
                bot.message_handler(func=func, **decorator_kwargs)(wrapper)
            else:
                pass
            return wrapper

        return decorator

    return handler
