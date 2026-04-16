from django.contrib import admin
from .models import ChatRoom, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model  = ChatMessage
    fields = ["author", "body", "created_at"]
    readonly_fields = ["created_at"]
    extra  = 0


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display  = ["name", "type", "company", "created_by", "created_at"]
    list_filter   = ["type", "company"]
    search_fields = ["name"]
    inlines       = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display  = ["room", "author", "body", "created_at"]
    list_filter   = ["room"]
    search_fields = ["body"]
