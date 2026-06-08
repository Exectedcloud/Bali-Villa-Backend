from django.db import models


class Review(models.Model):
    # Linked to a completed booking; nullable so seeded/imported reviews can exist without one
    booking = models.OneToOneField(
        'bookings.Booking',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='review',
    )
    guest = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='reviews',
    )
    villa = models.ForeignKey(
        'villas.Villa',
        on_delete=models.PROTECT,
        related_name='reviews',
    )
    # Rating on a 0–10 scale (matches mock data: 9.4, 9.7, etc.)
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    # Sub-ratings (also 0–10)
    rating_cleanliness = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    rating_accuracy = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    rating_checkin = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    rating_location = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    rating_value = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    rating_communication = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    # Review text — stored bilingually; DeepL fills missing translation on submit
    text_original = models.TextField()
    text_original_lang = models.CharField(
        max_length=5,
        choices=[('zh', 'Chinese'), ('en', 'English')],
        default='zh',
    )
    text_translated = models.TextField(blank=True)
    text_translated_lang = models.CharField(max_length=5, blank=True)
    # Host's public reply
    host_response = models.TextField(blank=True)
    host_replied_at = models.DateTimeField(null=True, blank=True)
    # Moderation
    is_visible = models.BooleanField(default=True)
    flagged_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reviews'
        ordering = ['-published_at']

    def __str__(self) -> str:
        return f'Review {self.pk}: {self.villa.slug} — {self.rating}/10'
