"""
Sender — central bot API hub.

Instance methods  (require message context — injected by make_handler decorator):
  sender.chat_id / sender.user_id / sender.message_id
  sender.text()       — send plain text (optionally i18n-translated)
  sender.send()       — i18n send
  sender.edit_text()  — edit current message text
  sender.edit()       — i18n edit
  sender.edit_markup()
  sender.delete()
  sender.answer()     — answer callback query

Static helpers  (no message context — use anywhere via Sender.<method>):
  Sender.set_bot(bot)          — called once by telegram/loader.py
  Sender.send_html(...)        — send HTML message to any chat
  Sender.edit_html(...)        — edit any message with HTML
  Sender.format_task(...)
  Sender.format_report(...)
  Sender.format_statistics(...)
  Sender.format_department_summary(...)
  Sender.paginate(...)
  Sender.get_db_user(...)
  Sender.require_role(...)
"""
from __future__ import annotations

import logging
from typing import TypeAlias

from telebot.async_telebot import AsyncTeleBot
from telebot.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

MessageLike: TypeAlias = Message | CallbackQuery
ReplyMarkup: TypeAlias = InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | None

_log = logging.getLogger("telegram.handlers")


class Sender:
    # ── Class-level bot reference — set once by loader.py ────────────────────
    _bot: AsyncTeleBot | None = None

    # ── Formatting lookup tables (class-level constants) ─────────────────────
    _STATUS_ICONS: dict[str, str] = {
        "new":         "🆕",
        "in_progress": "⚙️",
        "completed":   "✅",
        "blocked":     "🔴",
        "cancelled":   "❌",
        "overdue":     "⚠️",
    }
    _PRIORITY_ICONS: dict[str, str] = {
        "low":    "⬇️",
        "medium": "➡️",
        "high":   "⬆️",
        "urgent": "🚨",
    }

    __slots__ = ("bot", "msg", "i18n")

    # =========================================================================
    # Constructor
    # =========================================================================

    def __init__(self, bot: AsyncTeleBot, msg: MessageLike, i18n) -> None:
        self.bot  = bot
        self.msg  = msg
        self.i18n = i18n

    # =========================================================================
    # Class-level bot wiring
    # =========================================================================

    @classmethod
    def set_bot(cls, bot: AsyncTeleBot) -> None:
        """Called once from telegram/loader.py after the bot instance is ready."""
        cls._bot = bot

    # =========================================================================
    # Instance properties
    # =========================================================================

    @property
    def chat_id(self) -> int:
        if isinstance(self.msg, Message):
            return self.msg.chat.id
        return self.msg.message.chat.id

    @property
    def user(self):
        return self.msg.from_user

    @property
    def message_id(self) -> int:
        if isinstance(self.msg, Message):
            return self.msg.message_id
        return self.msg.message.message_id

    @property
    def user_id(self) -> int:
        return self.msg.from_user.id

    # =========================================================================
    # i18n
    # =========================================================================

    @property
    def lang(self) -> str:
        return self.i18n.get_user_lang(self.user_id)

    def tr(self, key: str, **kwargs) -> str:
        return self.i18n.gettext(self.lang, key, **kwargs)

    # =========================================================================
    # Instance message methods  (respond to current message context)
    # =========================================================================

    async def text(
        self,
        slug: str,
        markup: ReplyMarkup = None,
        translate: bool = True,
        **kwargs,
    ) -> Message:
        content = self.tr(slug, **kwargs) if translate else slug.format(**kwargs)
        return await self.bot.send_message(
            self.chat_id,
            text=content,
            reply_markup=markup,
            disable_web_page_preview=True,
        )

    async def send(self, key: str, markup: ReplyMarkup = None, **kwargs) -> Message:
        return await self.text(self.tr(key, **kwargs), markup=markup)

    async def edit_text(
        self,
        text: str,
        markup: ReplyMarkup = None,
        **kwargs,
    ) -> Message | None:
        content = text.format(**kwargs) if kwargs else text
        try:
            return await self.bot.edit_message_text(
                text=content,
                chat_id=self.chat_id,
                message_id=self.message_id,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
        except Exception as exc:
            if "message is not modified" in str(exc):
                return None
            if markup:
                try:
                    return await self.bot.edit_message_reply_markup(
                        chat_id=self.chat_id,
                        message_id=self.message_id,
                        reply_markup=markup,
                    )
                except Exception:
                    pass
            raise

    async def edit(self, key: str, markup: ReplyMarkup = None, **kwargs) -> Message | None:
        return await self.edit_text(self.tr(key, **kwargs), markup=markup)

    async def edit_markup(self, markup: ReplyMarkup = None) -> None:
        try:
            await self.bot.edit_message_reply_markup(
                chat_id=self.chat_id,
                message_id=self.message_id,
                reply_markup=markup,
            )
        except Exception:
            pass

    async def delete(self) -> None:
        try:
            await self.bot.delete_message(self.chat_id, self.message_id)
        except Exception:
            pass

    async def answer(self, text: str = "", show_alert: bool = False) -> None:
        if isinstance(self.msg, CallbackQuery):
            try:
                await self.bot.answer_callback_query(
                    self.msg.id, text=text, show_alert=show_alert
                )
            except Exception:
                pass

    # =========================================================================
    # Static helpers — send to any chat (no message context needed)
    # =========================================================================

    @staticmethod
    async def send_html(
        chat_id: int,
        text: str,
        markup=None,
        disable_preview: bool = True,
    ):
        return await Sender._bot.send_message(
            chat_id,
            text,
            parse_mode="HTML",
            reply_markup=markup,
            disable_web_page_preview=disable_preview,
        )

    @staticmethod
    async def edit_html(
        chat_id: int,
        message_id: int,
        text: str,
        markup=None,
    ):
        try:
            return await Sender._bot.edit_message_text(
                text,
                chat_id,
                message_id,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
            )
        except Exception as exc:
            if "message is not modified" not in str(exc):
                _log.debug("edit_html failed: %s", exc)
        return None

    # =========================================================================
    # Static formatting helpers
    # =========================================================================

    @staticmethod
    def format_task(task, show_instructions: bool = False) -> str:
        icon    = Sender._STATUS_ICONS.get(task.status, "📋")
        p_icon  = Sender._PRIORITY_ICONS.get(task.priority, "")
        due_str = task.due_at.strftime("%d.%m.%Y %H:%M") if task.due_at else "—"
        assignee = ""
        if task.assigned_user:
            assignee = f"\n👤 Xodim: {task.assigned_user.get_display_name()}"
        elif task.assigned_department:
            assignee = f"\n🏢 Bo'lim: {task.assigned_department.name}"
        overdue_badge = " ⚠️" if task.is_overdue else ""
        lines = [
            f"{icon} <b>{task.title}</b>{overdue_badge}",
            f"{p_icon} Ustuvorlik: <b>{task.get_priority_display()}</b>",
            f"📊 Holat: {task.get_status_display()}",
            f"📅 Muddat: {due_str}",
        ]
        if assignee:
            lines.append(assignee.strip())
        if task.description:
            lines.append(f"\n📄 <i>{task.description[:300]}</i>")
        if show_instructions and task.instructions:
            lines.append(f"\n📋 Ko'rsatmalar:\n{task.instructions[:500]}")
        return "\n".join(lines)

    @staticmethod
    def format_report(report) -> str:
        status_icons = {"submitted": "📤", "accepted": "✅", "rejected": "❌"}
        icon      = status_icons.get(report.status, "📊")
        emp_name  = report.employee.get_display_name() if report.employee else "—"
        task_title = report.task.title if report.task else "—"
        submitted  = report.submitted_at.strftime("%d.%m.%Y %H:%M")
        lines = [
            f"{icon} <b>Hisobot</b>",
            f"👤 Xodim: <b>{emp_name}</b>",
            f"📋 Vazifa: {task_title}",
            f"📅 Yuborilgan: {submitted}",
            f"📊 Holat: {report.get_status_display()}",
        ]
        if report.text:
            lines.append(f"\n✍️ Matn:\n<i>{report.text[:800]}</i>")
        if report.manager_comment:
            lines.append(f"\n💬 Menejer izohi: <i>{report.manager_comment}</i>")
        attach_count = report.attachments.count() if hasattr(report, "attachments") else 0
        if attach_count:
            lines.append(f"\n📎 Ilovalar: {attach_count} ta")
        return "\n".join(lines)

    @staticmethod
    def format_statistics(stats: dict) -> str:
        return (
            f"📈 <b>Umumiy statistika</b>\n\n"
            f"🏢 Bo'limlar: <b>{stats.get('total_departments', 0)}</b>\n"
            f"👥 Xodimlar: <b>{stats.get('total_employees', 0)}</b>\n\n"
            f"📋 Jami vazifalar: <b>{stats.get('total_tasks', 0)}</b>\n"
            f"  ⚙️ Faol: {stats.get('active_tasks', 0)}\n"
            f"  ✅ Bajarildi: {stats.get('completed_tasks', 0)}\n"
            f"  ⚠️ Muddati o'tdi: {stats.get('overdue_tasks', 0)}\n\n"
            f"📊 Jami hisobotlar: <b>{stats.get('total_reports', 0)}</b>\n"
            f"  ✅ Qabul qilindi: {stats.get('accepted_reports', 0)}\n"
            f"  📤 Kutmoqda: {stats.get('pending_reports', 0)}"
        )

    @staticmethod
    def format_department_summary(s: dict) -> str:
        dept = s.get("department")
        name = dept.name if dept else "—"
        return (
            f"🏢 <b>{name}</b>\n\n"
            f"👥 A'zolar: <b>{s.get('total_members', 0)}</b> (xodimlar: {s.get('employees_count', 0)})\n\n"
            f"📋 Vazifalar: <b>{s.get('total_tasks', 0)}</b>\n"
            f"🆕 Yangi: {s.get('new_tasks', 0)}\n"
            f"⚙️ Jarayonda: {s.get('in_progress', 0)}\n"
            f"✅ Bajarildi: {s.get('completed', 0)}\n"
            f"🔴 Bloklandi: {s.get('blocked', 0)}\n"
            f"⚠️ Muddati o'tdi: {s.get('overdue', 0)}\n\n"
            f"📊 Hisobotlar: {s.get('total_reports', 0)} jami, "
            f"{s.get('accepted_reports', 0)} qabul qilindi"
        )

    # =========================================================================
    # Static pagination helper
    # =========================================================================

    @staticmethod
    def paginate(items: list, page: int, per_page: int = 5) -> tuple[list, int, int]:
        """Return (page_items, total_pages, clamped_page)."""
        total       = len(items)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page        = max(0, min(page, total_pages - 1))
        start       = page * per_page
        return items[start: start + per_page], total_pages, page

    # =========================================================================
    # Static DB / auth helpers
    # =========================================================================

    @staticmethod
    async def get_db_user(telegram_id: int):
        """Fetch the active DB user by telegram_id, or None."""
        from apps.users.services import aget_user_by_telegram_id
        return await aget_user_by_telegram_id(telegram_id)

    @staticmethod
    async def require_role(telegram_id: int, chat_id: int, *roles: str):
        """
        Return the DB user if they hold one of the given roles.
        Send an error and return None otherwise.
        """
        user = await Sender.get_db_user(telegram_id)
        if not user:
            await Sender.send_html(chat_id, "❌ Foydalanuvchi topilmadi. /start bosing.")
            return None
        if not user.has_role:
            await Sender.send_html(
                chat_id, "⚠️ Sizga hali rol tayinlanmagan. Administrator bilan bog'laning."
            )
            return None
        if roles and user.role not in roles:
            await Sender.send_html(chat_id, "❌ Sizda ushbu amalni bajarish uchun ruxsat yo'q.")
            return None
        return user
