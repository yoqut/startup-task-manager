from telebot.asyncio_handler_backends import BaseMiddleware, CancelUpdate


class FloodMiddleware(BaseMiddleware):
    def __init__(self, limit, bot, message_text) -> None:
        super().__init__()
        self.last_time = {}
        self.bot = bot
        self.message_text = message_text
        self.limit = limit
        self.update_types = ['message']

    async def pre_process(self, message, data):
        if not message.from_user.id in self.last_time:
            self.last_time[message.from_user.id] = message.date
            return None

        if message.date - self.last_time[message.from_user.id] < self.limit:

            await self.bot.send_message(message.chat.id, self.message_text)
            return CancelUpdate()

        self.last_time[message.from_user.id] = message.date
        return None

    async def post_process(self, message, data, exception):
        pass


