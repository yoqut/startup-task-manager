from telebot.callback_data import CallbackData

from core.keyboards import InlineKeyboardBuilder
from core.utils.i18n import I18nEngine


def tariff_inl(lang: str = "uz"):

    tariffs = "standard", "pro", "premium"

    try:
        from apps.tariffs.services import get_tariffs
        tariffs = get_tariffs()
    except Exception as e:
        pass

    i18n = I18nEngine()
    tariff_factory = CallbackData("title", prefix="plans")
    markup = InlineKeyboardBuilder(lang, i18n.gettext)

    for i in tariffs:
        markup.button(i, callback_data=tariff_factory.new(i))

    return markup.build()



