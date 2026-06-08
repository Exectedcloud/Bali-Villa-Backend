from django.db import models


class Payment(models.Model):
    METHOD_WECHAT = 'wechat_pay'
    METHOD_ALIPAY = 'alipay'
    METHOD_UNIONPAY = 'unionpay'
    METHOD_CARD = 'card'
    METHOD_CHOICES = [
        (METHOD_WECHAT, 'WeChat Pay'),
        (METHOD_ALIPAY, 'Alipay'),
        (METHOD_UNIONPAY, 'UnionPay'),
        (METHOD_CARD, 'International Card'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'
    STATUS_PARTIALLY_REFUNDED = 'partially_refunded'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_REFUNDED, 'Refunded'),
        (STATUS_PARTIALLY_REFUNDED, 'Partially Refunded'),
    ]

    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.PROTECT,
        related_name='payments',
    )
    provider = models.CharField(max_length=50, default='airwallex')
    # Airwallex payment intent ID
    awx_payment_intent_id = models.CharField(max_length=200, unique=True)
    # Airwallex conversion ID — set after payment confirmed + FX conversion executed
    awx_conversion_id = models.CharField(max_length=200, blank=True)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_PENDING)
    # Amount charged to guest in CNY
    amount_cny = models.DecimalField(max_digits=12, decimal_places=2)
    # Amount received by platform in IDR after FX conversion
    amount_idr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # FX snapshot at payment time
    fx_rate = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    # Raw webhook payload from Airwallex for audit trail
    awx_webhook_payload = models.JSONField(default=dict)
    failed_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Payment {self.awx_payment_intent_id} — {self.status}'


class Payout(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    # Payout reference shown to hosts, e.g. 'BVP-2026-0501'
    reference = models.CharField(max_length=30, unique=True)
    host = models.ForeignKey(
        'users.HostProfile',
        on_delete=models.PROTECT,
        related_name='payouts',
    )
    booking = models.ForeignKey(
        'bookings.Booking',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='payouts',
    )
    amount_idr = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=100, blank=True)  # e.g. 'Bank Transfer — BCA'
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    # When the payout was initiated to the host's bank
    initiated_at = models.DateTimeField(null=True, blank=True)
    # When the payout was confirmed received
    paid_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payouts'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.reference
