from django.db import models


class Conversation(models.Model):
    # Linked to a specific booking (null if pre-booking enquiry)
    booking = models.OneToOneField(
        'bookings.Booking',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='conversation',
    )
    guest = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='guest_conversations',
    )
    host = models.ForeignKey(
        'users.HostProfile',
        on_delete=models.CASCADE,
        related_name='host_conversations',
    )
    villa = models.ForeignKey(
        'villas.Villa',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='conversations',
    )
    # Denormalised: last message preview for inbox list
    last_message_preview = models.CharField(max_length=300, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    # Unread counts — refreshed on each message send/read
    guest_unread_count = models.IntegerField(default=0)
    host_unread_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversations'
        ordering = ['-last_message_at']

    def __str__(self) -> str:
        return f'Conv {self.pk}: {self.guest.email} ↔ {self.host.display_name}'


class Message(models.Model):
    LANG_ZH = 'zh'
    LANG_EN = 'en'
    LANG_CHOICES = [(LANG_ZH, 'Chinese'), (LANG_EN, 'English')]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    # Original text as typed by the sender
    body_original = models.TextField()
    body_original_lang = models.CharField(max_length=5, choices=LANG_CHOICES, default=LANG_ZH)
    # DeepL translation — filled async by Celery within ~1 second of send
    body_translated = models.TextField(blank=True)
    body_translated_lang = models.CharField(max_length=5, choices=LANG_CHOICES, blank=True)
    # Optional attachment (Cloudflare R2 URL)
    attachment_url = models.URLField(max_length=500, blank=True)
    attachment_type = models.CharField(max_length=20, blank=True)  # 'image', 'pdf', etc.
    is_read_by_guest = models.BooleanField(default=False)
    is_read_by_host = models.BooleanField(default=False)
    # Per-message read timestamp (spec §20)
    read_at = models.DateTimeField(null=True, blank=True)
    # DeepL translation quality — 0.95 default, None if translation failed (spec §19)
    translation_confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'Msg {self.pk} in conv {self.conversation_id}'
