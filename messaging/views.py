from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from services.translation import translate, translate_to_all
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from villas.models import Villa


def _translate_with_confidence(text: str, target_lang: str) -> tuple:
    """Legacy helper — kept for any external callers. Returns (translated_text, confidence)."""
    if not text or not text.strip():
        return '', None
    translated = translate(text, target_lang)
    confidence = Decimal('0.950') if translated and translated != text else None
    return translated, confidence


def _translate_all_with_confidence(text: str, source_lang: str) -> tuple:
    """Translate to all languages. Returns (translations_dict, confidence)."""
    if not text or not text.strip():
        return {}, None
    translations = translate_to_all(text, source_lang)
    any_translated = any(v and k != source_lang for k, v in translations.items())
    confidence = Decimal('0.950') if any_translated else None
    return translations, confidence


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        convs = (
            Conversation.objects
            .filter(guest=request.user)
            .select_related('villa', 'host__user')
            .prefetch_related('villa__photos')
            .order_by('-last_message_at')
        )
        return Response({'conversations': ConversationSerializer(convs, many=True).data})

    def post(self, request):
        villa_id = request.data.get('villaId')
        if not villa_id:
            return Response({'error': 'villaId required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            villa = Villa.objects.select_related('host__user').get(
                pk=villa_id, status=Villa.STATUS_PUBLISHED
            )
        except Villa.DoesNotExist:
            return Response({'error': 'Villa not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Return existing conversation if one already exists for this guest+villa+host
        conv = Conversation.objects.filter(
            guest=request.user, villa=villa, host=villa.host
        ).first()
        created = False
        if not conv:
            conv = Conversation.objects.create(
                guest=request.user, villa=villa, host=villa.host
            )
            created = True

        conv_full = (
            Conversation.objects
            .select_related('villa', 'host__user')
            .prefetch_related('villa__photos')
            .get(pk=conv.pk)
        )
        resp_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response({'conversation': ConversationSerializer(conv_full).data}, status=resp_status)


class MessageListView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_conv(self, request, pk):
        try:
            return Conversation.objects.select_related('host__user').get(
                pk=pk, guest=request.user
            )
        except Conversation.DoesNotExist:
            return None

    def get(self, request, pk):
        conv = self._get_conv(request, pk)
        if not conv:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Mark conversation as read for the guest
        if conv.guest_unread_count > 0:
            conv.guest_unread_count = 0
            conv.save(update_fields=['guest_unread_count'])

        messages = Message.objects.filter(conversation=conv)
        return Response({
            'messages': MessageSerializer(
                messages, many=True,
                context={'conversation': conv, 'request': request},
            ).data
        })

    def post(self, request, pk):
        conv = self._get_conv(request, pk)
        if not conv:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        text = request.data.get('text', '').strip()
        if not text:
            return Response({'error': 'text is required.'}, status=status.HTTP_400_BAD_REQUEST)

        lang = request.data.get('lang') or getattr(request.user, 'preferred_language', None) or request.user.locale or 'zh'
        if lang not in ('zh', 'en', 'id'):
            lang = 'zh'

        translations, confidence = _translate_all_with_confidence(text, lang)
        # Mirror primary translation into legacy field (en for zh/id senders, zh for en senders)
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
        conv.host_unread_count += 1
        conv.save(update_fields=['last_message_preview', 'last_message_at', 'host_unread_count'])

        return Response(
            {'message': MessageSerializer(msg, context={'conversation': conv, 'request': request}).data},
            status=status.HTTP_201_CREATED,
        )


class MessageReadView(APIView):
    """POST /api/v1/messages/<id>/read/ — recipient marks a message as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            msg = Message.objects.select_related(
                'conversation__guest', 'conversation__host__user'
            ).get(pk=pk)
        except Message.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        conv = msg.conversation
        is_participant = (
            conv.guest == request.user or conv.host.user == request.user
        )
        if not is_participant:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if msg.sender == request.user:
            return Response(
                {'error': 'You cannot mark your own message as read.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if msg.read_at is None:
            msg.read_at = timezone.now()
            msg.save(update_fields=['read_at'])

        return Response({
            'messageId': msg.id,
            'readAt': msg.read_at.isoformat(),
        })
