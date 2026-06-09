from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import HostProfile
from users.permissions import HasHostRole
from .models import Conversation, Message
from .serializers import MessageSerializer
from .views import _translate_with_confidence, _translate_all_with_confidence


class HostConversationSerializer(serializers.ModelSerializer):
    villaId = serializers.IntegerField(source='villa_id')
    guestId = serializers.IntegerField(source='guest_id')
    lastMessageAt = serializers.DateTimeField(source='last_message_at')
    lastMessagePreview = serializers.CharField(source='last_message_preview')
    unreadHost = serializers.IntegerField(source='host_unread_count')
    villaTitle = serializers.SerializerMethodField()
    villaPhoto = serializers.SerializerMethodField()
    guestName = serializers.SerializerMethodField()
    guestAvatar = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'villaId', 'guestId',
            'lastMessageAt', 'lastMessagePreview', 'unreadHost',
            'villaTitle', 'villaPhoto', 'guestName', 'guestAvatar',
        ]

    def get_villaTitle(self, obj):
        return obj.villa.title_en if obj.villa else ''

    def get_villaPhoto(self, obj):
        if not obj.villa:
            return ''
        photo = obj.villa.photos.order_by('order', 'created_at').first()
        return photo.url if photo else ''

    def get_guestName(self, obj):
        name = f'{obj.guest.first_name} {obj.guest.last_name}'.strip()
        return name or obj.guest.email

    def get_guestAvatar(self, obj):
        return obj.guest.avatar_url or ''


class HostConversationListView(APIView):
    permission_classes = [HasHostRole]

    def _get_host(self, user):
        try:
            return user.host_profile
        except HostProfile.DoesNotExist:
            return None

    def get(self, request):
        host = self._get_host(request.user)
        if not host:
            return Response({'error': 'Not a host account.'}, status=status.HTTP_403_FORBIDDEN)
        convs = (
            Conversation.objects
            .filter(host=host)
            .select_related('villa', 'guest')
            .prefetch_related('villa__photos')
            .order_by('-last_message_at')
        )
        return Response({'conversations': HostConversationSerializer(convs, many=True).data})


class HostMessageListView(APIView):
    permission_classes = [HasHostRole]

    def _get_conv(self, request, pk):
        try:
            host = request.user.host_profile
        except HostProfile.DoesNotExist:
            return None, None
        try:
            conv = Conversation.objects.select_related('guest').get(pk=pk, host=host)
            return conv, host
        except Conversation.DoesNotExist:
            return None, None

    def get(self, request, pk):
        conv, _ = self._get_conv(request, pk)
        if not conv:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if conv.host_unread_count > 0:
            conv.host_unread_count = 0
            conv.save(update_fields=['host_unread_count'])

        messages = Message.objects.filter(conversation=conv)
        return Response({
            'messages': MessageSerializer(
                messages, many=True,
                context={'conversation': conv, 'request': request},
            ).data
        })

    def post(self, request, pk):
        conv, _ = self._get_conv(request, pk)
        if not conv:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        text = request.data.get('text', '').strip()
        if not text:
            return Response({'error': 'text is required.'}, status=status.HTTP_400_BAD_REQUEST)

        lang = request.data.get('lang') or getattr(request.user, 'preferred_language', None) or 'en'
        if lang not in ('zh', 'en', 'id'):
            lang = 'en'

        translations, confidence = _translate_all_with_confidence(text, lang)
        # Mirror primary translation into legacy field (zh for en/id senders, en for zh senders)
        legacy_lang = 'zh' if lang == 'en' else 'en'
        body_translated = translations.get(legacy_lang, '')

        msg = Message.objects.create(
            conversation=conv,
            sender=request.user,
            body_original=text,
            body_original_lang=lang,
            translations=translations,
            body_translated=body_translated,
            body_translated_lang=legacy_lang if body_translated else '',
            translation_confidence=confidence,
        )

        conv.last_message_preview = text[:299]
        conv.last_message_at = timezone.now()
        conv.guest_unread_count += 1
        conv.save(update_fields=['last_message_preview', 'last_message_at', 'guest_unread_count'])

        return Response(
            {'message': MessageSerializer(msg, context={'conversation': conv, 'request': request}).data},
            status=status.HTTP_201_CREATED,
        )
