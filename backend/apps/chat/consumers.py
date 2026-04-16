"""
ChatConsumer — async WebSocket consumer.
Each room has its own channel group: chat_<room_id>

Message types sent/received (JSON):
  Client → Server:
    { "type": "message", "body": "...", "related_task": null, "related_report": null }

  Server → Client:
    { "type": "message",   "message": { id, author_id, author_name, author_role, body, created_at, room_id } }
    { "type": "error",     "message": "..." }
    { "type": "connected", "room_id": "..." }
"""
import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.utils import timezone

from .models import ChatRoom, ChatMessage


class ChatConsumer(AsyncJsonWebsocketConsumer):

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self):
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.room_id    = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = f"chat_{self.room_id}"
        self.user       = user

        # Verify room exists and user has access
        room = await self.get_room()
        if room is None:
            await self.close(code=4004)
            return
        if not await self.check_access(room):
            await self.close(code=4003)
            return

        self.room = room
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected", "room_id": self.room_id})

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # ── Incoming messages ─────────────────────────────────────────────────────

    async def receive_json(self, content):
        msg_type = content.get("type")

        if msg_type == "message":
            body = (content.get("body") or "").strip()
            if not body:
                return
            message = await self.save_message(
                body=body,
                related_task_id=content.get("related_task"),
                related_report_id=content.get("related_report"),
            )
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "chat.message", "payload": self.serialize(message)},
            )
            # Bridge to Telegram if this room is linked
            if self.room.telegram_chat_id:
                await self.forward_to_telegram(message)

            # Trigger agent chat monitoring (fire-and-forget)
            await self.maybe_trigger_monitor(message)

    # ── Group message handler ─────────────────────────────────────────────────

    async def chat_message(self, event):
        await self.send_json({"type": "message", "message": event["payload"]})

    # ── DB helpers ────────────────────────────────────────────────────────────

    @database_sync_to_async
    def get_room(self):
        try:
            return ChatRoom.objects.select_related("company").get(
                pk=self.room_id, company=self.user.company
            )
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def check_access(self, room):
        return room.can_access(self.user)

    @database_sync_to_async
    def save_message(self, body, related_task_id=None, related_report_id=None):
        msg = ChatMessage.objects.create(
            room=self.room,
            author=self.user,
            body=body,
            related_task_id=related_task_id,
            related_report_id=related_report_id,
        )
        # Bump room.updated_at so it floats to top of sidebar
        ChatRoom.objects.filter(pk=self.room_id).update(updated_at=timezone.now())
        return msg

    @database_sync_to_async
    def maybe_trigger_monitor(self, message):
        """
        If any agent has monitor_chats=True and is linked to this room's department,
        fire a lightweight async chat analysis task every 10th message.
        """
        try:
            from apps.agents.models import AgentConfiguration
            from apps.agents.tasks import monitor_chat_room

            room = self.room
            dept_ids = list(room.org_units.values_list("pk", flat=True))

            # Find agents that monitor chats and are linked to these departments
            # (or have no departments = monitors all)
            agents_qs = AgentConfiguration.objects.filter(
                company=room.company, is_enabled=True, monitor_chats=True,
            ).filter(
                models.Q(departments__isnull=True) | models.Q(departments__in=dept_ids)
                if dept_ids else models.Q(departments__isnull=True)
            ).distinct()

            if not agents_qs.exists():
                return

            # Only trigger every 10th message to avoid overloading
            msg_count = room.messages.count()
            if msg_count % 10 == 0:
                monitor_chat_room.delay(str(room.id), str(room.company_id))
        except Exception:
            pass  # Never break chat for monitoring failures

    @database_sync_to_async
    def forward_to_telegram(self, message):
        """Send the message to the linked Telegram chat (runs in thread pool)."""
        from apps.integrations.telegram.sender import send_message
        author_name = message.author.full_name if message.author else "Unknown"
        try:
            send_message(
                self.room.telegram_chat_id,
                f"*{author_name}:* {message.body}",
            )
        except Exception:
            pass  # Never break chat if Telegram is down

    @staticmethod
    def serialize(msg):
        return {
            "id":           str(msg.id),
            "room_id":      str(msg.room_id),
            "author_id":    str(msg.author_id) if msg.author_id else None,
            "author_name":  msg.author.full_name if msg.author else "Unknown",
            "author_role":  msg.author.role if msg.author else "",
            "body":         msg.body,
            "created_at":   msg.created_at.isoformat(),
            "related_task":   str(msg.related_task_id)   if msg.related_task_id   else None,
            "related_report": str(msg.related_report_id) if msg.related_report_id else None,
        }
