"""
Reply keyboards — only the phone-contact picker is kept here because
request_contact=True requires a ReplyKeyboardButton (Telegram limitation).

All other menus and wizard controls have been converted to inline keyboards.
See telegram/keyboards/inlines.py.
"""
from telebot.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def contact_kb() -> ReplyKeyboardMarkup:
    """Ask the user to share their phone number."""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("📱 Telefon raqamni ulashish", request_contact=True))
    markup.add(KeyboardButton("❌ Bekor qilish"))
    return markup
