from django.contrib import admin
from apps.conversations.models import ConversationMessage, ConversationSession


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "session_type", "status", "scenario", "total_tokens_used", "created_at")
    list_filter = ("status",)


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "message_order", "token_count", "created_at")
    list_filter = ("role",)
