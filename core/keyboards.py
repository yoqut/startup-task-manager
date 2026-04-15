from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

import telebot.types as types
from telebot.callback_data import CallbackData

# ---------------------------------------------------------------------------
# Type alias for optional i18n translator
# ---------------------------------------------------------------------------


def _t(lang, text: str, tr, **kwargs) -> str:
    """Apply translator if provided, otherwise return raw text."""
    return tr(lang, text, **kwargs) if tr else text.format(**kwargs)


ButtonStyle = Literal["primary", "success", "danger"]


# ---------------------------------------------------------------------------
# 0. StyledInlineKeyboardButton — adds Telegram Bot API `style` field
# ---------------------------------------------------------------------------
class StyledInlineKeyboardButton(types.InlineKeyboardButton):
    """
    InlineKeyboardButton extended with the optional `style` field
    from the Telegram Bot API spec:
      - "primary"  → blue
      - "success"  → green
      - "danger"   → red
    """

    def __init__(self, *args, style: ButtonStyle | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._style = style

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self._style:
            d["style"] = self._style
        return d


# ---------------------------------------------------------------------------
# 1. BaseKeyboard – abstract contract
# ---------------------------------------------------------------------------
class BaseKeyboard(ABC):
    """Abstract base for all keyboard builders."""

    @abstractmethod
    def build(self) -> types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup:
        """Return the final Telegram markup object."""

    @abstractmethod
    def reset(self) -> "BaseKeyboard":
        """Clear internal state and return self for chaining."""

# ---------------------------------------------------------------------------
# 3. InlineKeyboardBuilder
# ---------------------------------------------------------------------------
class InlineKeyboardBuilder(BaseKeyboard):
    """
    Fluent builder for InlineKeyboardMarkup.

    Usage:
        markup = (
            InlineKeyboardBuilder(tr=_)
            .button("Home", callback_data="home")
            .button("Settings", callback_data="settings")
            .row()
            .button("Back", callback_data="back")
            .build()
        )
    """

    def __init__(self, lang: str = "uz", tr = None) -> None:
        self._tr = tr
        self.lang = lang
        self._rows: list[list[types.InlineKeyboardButton]] = [[]]

    # -- mutation helpers ----------------------------------------------------

    def button(
        self,
        text: str,
        *,
        callback_data: str | None = None,
        url: str | None = None,
        style: ButtonStyle | None = None,
        switch_inline_query: str | None = None,
        switch_inline_query_current_chat: str | None = None,
        **kwargs
    ) -> "InlineKeyboardBuilder":
        btn = StyledInlineKeyboardButton(
            text=_t(self.lang, text, self._tr, **kwargs),
            callback_data=callback_data,
            url=url,
            style=style,
            switch_inline_query=switch_inline_query,
            switch_inline_query_current_chat=switch_inline_query_current_chat,
        )
        self._rows[-1].append(btn)
        return self

    def row(self) -> "InlineKeyboardBuilder":
        """Start a new row (no-op if current row is already empty)."""
        if self._rows[-1]:
            self._rows.append([])
        return self

    def add_row(self, *buttons: tuple[str, str]) -> "InlineKeyboardBuilder":
        """Convenience: add a full row of (text, callback_data) pairs at once."""
        self.row()
        for text, cb in buttons:
            self.button(text, callback_data=cb)
        return self.row()

    # -- BaseKeyboard --------------------------------------------------------

    def build(self) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup()
        for row in self._rows:
            if row:
                markup.row(*row)
        return markup

    def reset(self) -> "InlineKeyboardBuilder":
        self._rows = [[]]
        return self


# ---------------------------------------------------------------------------
# 4. ReplyKeyboardBuilder
# ---------------------------------------------------------------------------
class ReplyKeyboardBuilder(BaseKeyboard):
    """
    Fluent builder for ReplyKeyboardMarkup.

    Usage:
        markup = (
            ReplyKeyboardBuilder(tr=_, resize_keyboard=True)
            .button("Menu")
            .button("Help")
            .row()
            .button("Back")
            .build()
        )
    """

    def __init__(
        self,
        tr = None,
        resize_keyboard: bool = True,
        one_time_keyboard: bool = False,
        selective: bool = False,
        input_field_placeholder: str | None = None,
    ) -> None:
        self._tr = tr
        self._resize = resize_keyboard
        self._one_time = one_time_keyboard
        self._selective = selective
        self._placeholder = input_field_placeholder
        self._rows: list[list[types.KeyboardButton]] = [[]]

    # -- mutation helpers ----------------------------------------------------

    def button(
        self,
        text: str,
        *,
        request_contact: bool = False,
        request_location: bool = False,
        **kwargs
    ) -> "ReplyKeyboardBuilder":
        btn = types.KeyboardButton(
            text=_t(text, self._tr, **kwargs),
            request_contact=request_contact,
            request_location=request_location,
        )
        self._rows[-1].append(btn)
        return self

    def row(self) -> "ReplyKeyboardBuilder":
        if self._rows[-1]:
            self._rows.append([])
        return self

    def add_row(self, *texts: str) -> "ReplyKeyboardBuilder":
        """Convenience: add a full row of plain text buttons at once."""
        self.row()
        for t in texts:
            self.button(t)
        return self.row()

    # -- BaseKeyboard --------------------------------------------------------

    def build(self) -> types.ReplyKeyboardMarkup:
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=self._resize,
            one_time_keyboard=self._one_time,
            selective=self._selective,
            input_field_placeholder=self._placeholder,
        )
        for row in self._rows:
            if row:
                markup.row(*row)
        return markup

    def reset(self) -> "ReplyKeyboardBuilder":
        self._rows = [[]]
        return self


# ---------------------------------------------------------------------------
# 5. Remove keyboard helper
# ---------------------------------------------------------------------------
def remove_keyboard(selective: bool = False) -> types.ReplyKeyboardRemove:
    return types.ReplyKeyboardRemove(selective=selective)


# ---------------------------------------------------------------------------
# EXAMPLE USAGE (comments only — not executed)
# ---------------------------------------------------------------------------
#
# ── Setup ──────────────────────────────────────────────────────────────────
#
# from keyboards import (
#     InlineKeyboardBuilder,
#     ReplyKeyboardBuilder,
#     CallbackDataFactory,
#     remove_keyboard,
# )
#
# # Optional i18n (e.g. GNU gettext or any callable)
# import gettext
# _ = gettext.gettext
#
#
# ── CallbackDataFactory ────────────────────────────────────────────────────
#
# page_cb = CallbackDataFactory("page", "action", "num")
#
# # Encode
# data = page_cb.new(action="go", num=3)   # → "page:go:3"
#
# # Decode inside handler
# @bot.callback_query_handler(func=lambda c: page_cb.filter(action="go") == ...)
# def handle_page(call):
#     parsed = page_cb.parse(call.data)
#     page = int(parsed["num"])
#
#
# ── InlineKeyboardBuilder ──────────────────────────────────────────────────
#
# markup = (
#     InlineKeyboardBuilder(tr=_)
#     .button("🏠 Home",     callback_data="home")
#     .button("⚙️ Settings", callback_data="settings")
#     .row()
#     .button("◀️ Back",     callback_data="back")
#     .build()
# )
# bot.send_message(chat_id, "Choose:", reply_markup=markup)
#
#
# ── ReplyKeyboardBuilder ───────────────────────────────────────────────────
#
# markup = (
#     ReplyKeyboardBuilder(tr=_, resize_keyboard=True, one_time_keyboard=True)
#     .add_row("📋 Menu", "❓ Help")
#     .button("📞 Share contact", request_contact=True)
#     .build()
# )
# bot.send_message(chat_id, "Use the menu:", reply_markup=markup)
#
#
# ── Remove keyboard ────────────────────────────────────────────────────────
#
# bot.send_message(chat_id, "Done.", reply_markup=remove_keyboard())
