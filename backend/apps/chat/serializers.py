from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import ChatRoom, ChatMessage

User = get_user_model()


class MessageAuthorSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model  = User
        fields = ["id", "full_name", "first_name", "last_name", "role"]


class ChatMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_role = serializers.CharField(source="author.role", read_only=True, default="")

    class Meta:
        model  = ChatMessage
        fields = [
            "id", "room", "author", "author_name", "author_role",
            "body", "created_at", "edited_at",
            "related_task", "related_report",
        ]
        read_only_fields = ["id", "author", "created_at", "edited_at"]

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.full_name
        return obj.author_display_name or "Telegram"


class ChatRoomSerializer(serializers.ModelSerializer):
    created_by_name  = serializers.CharField(source="created_by.full_name", read_only=True, default="")
    last_message     = serializers.SerializerMethodField()
    unread_count     = serializers.SerializerMethodField()
    org_unit_names   = serializers.SerializerMethodField()

    class Meta:
        model  = ChatRoom
        fields = [
            "id", "name", "description", "type",
            "org_units", "org_unit_names",
            "members",
            "related_task", "related_report",
            "telegram_chat_id",
            "created_by", "created_by_name",
            "created_at", "updated_at",
            "last_message", "unread_count",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        if not msg:
            return None
        return {
            "body":        msg.body[:80],
            "author_name": msg.author.full_name if msg.author else "",
            "created_at":  msg.created_at,
        }

    def get_unread_count(self, obj):
        # Placeholder — full unread tracking can be added later
        return 0

    def get_org_unit_names(self, obj):
        return list(obj.org_units.values_list("name", flat=True))
