from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ('sender', 'body_original_lang', 'body_original', 'body_translated', 'created_at')
    readonly_fields = ('created_at',)
    ordering = ('created_at',)
    show_change_link = True


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'guest', 'host', 'villa', 'last_message_at', 'guest_unread_count', 'host_unread_count')
    list_filter = ('host',)
    search_fields = ('guest__email', 'host__display_name', 'villa__slug')
    readonly_fields = ('created_at', 'updated_at', 'last_message_at')
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'body_original_lang', 'body_translated_lang', 'created_at')
    list_filter = ('body_original_lang', 'body_translated_lang')
    search_fields = ('sender__email', 'body_original')
    readonly_fields = ('created_at',)
