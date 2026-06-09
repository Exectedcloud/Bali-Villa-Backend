from rest_framework import serializers
from .models import Conversation, Message


class ConversationSerializer(serializers.ModelSerializer):
    villaId = serializers.IntegerField(source='villa_id')
    hostId = serializers.IntegerField(source='host_id')
    lastMessageAt = serializers.DateTimeField(source='last_message_at')
    lastMessagePreview = serializers.CharField(source='last_message_preview')
    unreadGuest = serializers.IntegerField(source='guest_unread_count')
    villaTitle = serializers.SerializerMethodField()
    villaPhoto = serializers.SerializerMethodField()
    hostName = serializers.SerializerMethodField()
    hostAvatar = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'villaId', 'hostId',
            'lastMessageAt', 'lastMessagePreview', 'unreadGuest',
            'villaTitle', 'villaPhoto', 'hostName', 'hostAvatar',
        ]

    def get_villaTitle(self, obj):
        return obj.villa.title_en if obj.villa else ''

    def get_villaPhoto(self, obj):
        if not obj.villa:
            return ''
        photo = obj.villa.photos.order_by('order', 'created_at').first()
        return photo.url if photo else ''

    def get_hostName(self, obj):
        return obj.host.display_name

    def get_hostAvatar(self, obj):
        return obj.host.user.avatar_url or ''


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    textZh = serializers.SerializerMethodField()
    textEn = serializers.SerializerMethodField()
    sentAt = serializers.DateTimeField(source='created_at')
    translated = serializers.SerializerMethodField()
    readAt = serializers.DateTimeField(source='read_at', allow_null=True, read_only=True)
    translationConfidence = serializers.DecimalField(
        source='translation_confidence', max_digits=4, decimal_places=3,
        allow_null=True, read_only=True,
    )
    translations = serializers.JSONField(read_only=True)
    bodyOriginalLang = serializers.CharField(source='body_original_lang', read_only=True)
    preferredText = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'textZh', 'textEn', 'sentAt', 'translated',
            'readAt', 'translationConfidence',
            'translations', 'bodyOriginalLang', 'preferredText',
        ]

    def get_sender(self, obj):
        conv = self.context['conversation']
        return 'guest' if obj.sender_id == conv.guest_id else 'host'

    def get_textZh(self, obj):
        t = obj.translations or {}
        if t.get('zh'):
            return t['zh']
        if obj.body_original_lang == 'zh':
            return obj.body_original
        return obj.body_translated or ''

    def get_textEn(self, obj):
        t = obj.translations or {}
        if t.get('en'):
            return t['en']
        if obj.body_original_lang == 'en':
            return obj.body_original
        return obj.body_translated or ''

    def get_translated(self, obj):
        return bool(obj.translations or obj.body_translated)

    def get_preferredText(self, obj):
        request = self.context.get('request')
        lang = 'en'
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            lang = getattr(request.user, 'preferred_language', None) or 'en'

        t = obj.translations or {}
        if t.get(lang):
            return t[lang]
        # Fall back through legacy fields
        if lang == obj.body_original_lang:
            return obj.body_original
        if obj.body_translated and obj.body_translated_lang == lang:
            return obj.body_translated
        return obj.body_original
