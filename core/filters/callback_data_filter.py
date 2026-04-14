
from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.callback_data import CallbackDataFilter

class F(AdvancedCustomFilter):
    """key='config' — universal filter for CallbackData factories."""
    key = 'config'

    async def check(self, call, config: CallbackDataFilter) -> bool:
        return config.check(query=call)
