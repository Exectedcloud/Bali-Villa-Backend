from django.db import models


class Booking(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PENDING_PAYMENT = 'pending_payment'
    STATUS_PENDING_APPROVAL = 'pending_approval'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_IN_HOUSE = 'in_house'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PENDING_PAYMENT, 'Pending Payment'),
        (STATUS_PENDING_APPROVAL, 'Pending Approval'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_IN_HOUSE, 'In House'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    # Booking reference shown to users, e.g. 'BV-2026-0042'
    reference = models.CharField(max_length=30, unique=True)
    guest = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    villa = models.ForeignKey(
        'villas.Villa',
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    check_in = models.DateField()
    check_out = models.DateField()
    # Denormalised for convenience (check_out - check_in in days)
    nights = models.IntegerField()
    adults = models.IntegerField(default=1)
    children = models.IntegerField(default=0)
    infants = models.IntegerField(default=0)

    # ── Pricing (all DecimalField, never FloatField) ──────────────────────────
    # IDR amounts — what the host receives / what the system tracks internally
    nightly_rate_idr = models.DecimalField(max_digits=14, decimal_places=2)
    cleaning_fee_idr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    service_fee_idr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_idr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_idr = models.DecimalField(max_digits=14, decimal_places=2)
    # CNY amounts — what the guest is charged
    base_price_cny = models.DecimalField(max_digits=12, decimal_places=2)
    cleaning_fee_cny = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_fee_cny = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_cny = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cny = models.DecimalField(max_digits=12, decimal_places=2)
    # Host payout amount in IDR (total minus platform commission)
    payout_idr = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # ── FX snapshot (required for reconciliation) ─────────────────────────────
    # All three rate fields stored per CLAUDE.md / fx-architecture.md
    mid_rate = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    awx_rate = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    client_rate = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    # Airwallex locked-rate quote ID (15-min TTL at reservation)
    fx_quote_id = models.CharField(max_length=200, blank=True)
    fx_quote_expires_at = models.DateTimeField(null=True, blank=True)

    # ── Promotions ────────────────────────────────────────────────────────────
    promo_code = models.CharField(max_length=50, null=True, blank=True)
    promo_discount_idr = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # ── Guests ────────────────────────────────────────────────────────────────
    additional_guests = models.JSONField(default=list)

    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    guest_note = models.TextField(blank=True)
    special_requests = models.JSONField(default=dict)
    # Internal note from host after approving/declining
    host_note = models.TextField(blank=True)
    # When the host responded to a pending approval request
    host_responded_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.reference
