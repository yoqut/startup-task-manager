from telebot.asyncio_handler_backends import BaseMiddleware, CancelUpdate
from apps.accounts.services import get_user

class NoRegisterMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.update_sensitive = True
        self.update_types = ['message', 'callback_query']

    async def pre_process(self, message, data):
        user = await get_user(message.from_user.id)
        if user:

        return CancelUpdate()


    async def post_process(self, message, data, ex):
        return message

