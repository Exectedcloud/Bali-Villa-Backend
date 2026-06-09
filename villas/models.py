from django.db import models


class Villa(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_PAUSED = 'paused'
    STATUS_PENDING_REVIEW = 'pending_review'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_PAUSED, 'Paused'),
        (STATUS_PENDING_REVIEW, 'Pending Review'),
    ]

    TYPE_VILLA = 'villa'
    TYPE_VACATION_HOME = 'vacation_home'
    TYPE_GUEST_HOUSE = 'guest_house'
    TYPE_HOTEL = 'hotel'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_VILLA, 'Villa'),
        (TYPE_VACATION_HOME, 'Vacation Home'),
        (TYPE_GUEST_HOUSE, 'Guest House'),
        (TYPE_HOTEL, 'Hotel'),
        (TYPE_OTHER, 'Other'),
    ]

    POLICY_FLEXIBLE = 'flexible'
    POLICY_MODERATE = 'moderate'
    POLICY_STRICT = 'strict'
    POLICY_CHOICES = [
        (POLICY_FLEXIBLE, 'Flexible'),
        (POLICY_MODERATE, 'Moderate'),
        (POLICY_STRICT, 'Strict'),
    ]

    host = models.ForeignKey(
        'users.HostProfile',
        on_delete=models.CASCADE,
        related_name='villas',
    )
    slug = models.SlugField(max_length=120, unique=True)
    title_zh = models.CharField(max_length=300)
    title_en = models.CharField(max_length=300)
    description_zh = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    property_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_VILLA)
    # Location — switch to PostGIS PointField when migrating to PostgreSQL
    location = models.CharField(max_length=500, blank=True)
    region = models.CharField(max_length=100, blank=True)  # e.g. 'Seminyak', 'Ubud'
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)  # hidden until booking confirmed
    bedrooms = models.IntegerField(default=1)
    beds = models.IntegerField(default=1)
    bathrooms = models.DecimalField(max_digits=4, decimal_places=1, default=1)
    max_guests = models.IntegerField(default=2)
    min_nights = models.IntegerField(default=1)
    max_nights = models.IntegerField(default=30)
    highlights = models.JSONField(default=list)
    pool = models.BooleanField(default=False)
    instant_book = models.BooleanField(default=False)
    cancellation_policy = models.CharField(max_length=10, choices=POLICY_CHOICES, default=POLICY_MODERATE)
    check_in_from = models.TimeField(null=True, blank=True)
    check_in_until = models.TimeField(null=True, blank=True)
    check_out_by = models.TimeField(null=True, blank=True)
    house_rules = models.JSONField(default=list)
    weekend_premium_pct = models.IntegerField(default=0)
    # Money fields: all DecimalField, never FloatField
    # Host sets price in IDR; system converts to CNY for guests
    base_price_idr = models.DecimalField(max_digits=14, decimal_places=2)
    # Display cache: CNY equivalent refreshed by Celery FX task. IDR is source of truth (see fx-architecture.md §8.1).
    base_price_cny = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cleaning_fee_idr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='verified_villas',
    )
    video_url = models.URLField(max_length=500, blank=True)
    rejection_reason = models.TextField(blank=True)
    # Denormalised for listing performance
    avg_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    review_count = models.IntegerField(default=0)
    # Cover image URL (first photo or explicitly set)
    cover_photo_url = models.URLField(max_length=500, blank=True)
    # e.g. ['balivilla_select', 'guest_favorite', 'instant_book']
    tags = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'villas'

    def __str__(self) -> str:
        return self.title_en or self.title_zh


class VillaPhoto(models.Model):
    villa = models.ForeignKey(Villa, on_delete=models.CASCADE, related_name='photos')
    url = models.URLField(max_length=500)
    caption_zh = models.CharField(max_length=300, blank=True)
    caption_en = models.CharField(max_length=300, blank=True)
    room_type = models.CharField(max_length=50, blank=True)
    # lower number = shown first
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'villa_photos'
        ordering = ['order', 'created_at']

    def __str__(self) -> str:
        return f'{self.villa.slug} photo {self.order}'


class VillaAmenity(models.Model):
    CATEGORY_CHOICES = [
        ('essentials', 'Essentials'),
        ('kitchen', 'Kitchen'),
        ('outdoor', 'Outdoor'),
        ('entertainment', 'Entertainment'),
        ('safety', 'Safety'),
        ('accessibility', 'Accessibility'),
    ]

    villa = models.ForeignKey(Villa, on_delete=models.CASCADE, related_name='amenities')
    key = models.CharField(max_length=100)   # machine key, e.g. 'wifi', 'private_pool'
    label_zh = models.CharField(max_length=200, blank=True)
    label_en = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='essentials')
    is_highlight = models.BooleanField(default=False)  # shown prominently in listing
    available = models.BooleanField(default=True)  # host can disable without deleting

    class Meta:
        db_table = 'villa_amenities'
        unique_together = ('villa', 'key')

    def __str__(self) -> str:
        return f'{self.villa.slug} — {self.key}'


class Availability(models.Model):
    STATUS_AVAILABLE = 'available'
    STATUS_BLOCKED = 'blocked'
    STATUS_BOOKED = 'booked'
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, 'Available'),
        (STATUS_BLOCKED, 'Blocked'),
        (STATUS_BOOKED, 'Booked'),
    ]

    villa = models.ForeignKey(Villa, on_delete=models.CASCADE, related_name='availability')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE)
    # Override nightly price for this specific date (null = use villa base price)
    price_override_idr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'availability'
        unique_together = ('villa', 'date')

    def __str__(self) -> str:
        return f'{self.villa.slug} {self.date} — {self.status}'


class Wishlist(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='wishlist_items',
    )
    villa = models.ForeignKey(
        Villa,
        on_delete=models.CASCADE,
        related_name='wishlisted_by',
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wishlists'
        unique_together = ('user', 'villa')

    def __str__(self) -> str:
        return f'{self.user.email} → {self.villa.slug}'
