"""
NoRegisterMiddleware — fetches (or creates) the DB User record for every
incoming update and attaches it to the handler data dict as ``data['db_user']``.

Every handler can do:
    user = data.get('db_user')
without an extra DB round-trip.

The middleware does NOT block unregistered users — that lets /start
run for brand-new visitors.  Role-based access control is enforced inside
individual handlers via telegram.utils.require_role().
"""
import logging

from telebot.asyncio_handler_backends import BaseMiddleware
from apps.users.services import get_or_create_user_by_telegram

logger = logging.getLogger("telegram.handlers")


class NoRegisterMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()
        self.update_sensitive = True
        self.update_types = ["message", "callback_query"]

    async def pre_process(self, message, data: dict):
        from_user = getattr(message, "from_user", None)
        if from_user is None:
            inner = getattr(message, "message", None)
            from_user = getattr(inner, "from_user", None)

        if from_user is None:
            data["db_user"] = None
            return None

        try:
            user, _created = await get_or_create_user_by_telegram(
                telegram_id=from_user.id,
                username=getattr(from_user, "username", "") or "",
                full_name=getattr(from_user, "full_name", "") or "",
            )
            data["db_user"] = user
        except Exception as exc:
            logger.error("NoRegisterMiddleware DB error: %s", exc)
            data["db_user"] = None

        return None

    async def post_process(self, message, data: dict, exception):
        pass
