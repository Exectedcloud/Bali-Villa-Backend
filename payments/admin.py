from django.contrib import admin
from .models import Payment, Payout


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('awx_payment_intent_id', 'booking', 'method', 'status', 'amount_cny', 'created_at')
    list_filter = ('status', 'method', 'provider')
    search_fields = ('awx_payment_intent_id', 'booking__reference')
    readonly_fields = ('created_at', 'updated_at', 'awx_payment_intent_id', 'awx_conversion_id')


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('reference', 'host', 'amount_idr', 'status', 'initiated_at', 'paid_at')
    list_filter = ('status',)
    search_fields = ('reference', 'host__display_name', 'host__user__email')
    readonly_fields = ('reference', 'created_at', 'updated_at', 'initiated_at', 'paid_at')
    actions = ['mark_completed']

    @admin.action(description='Mark selected payouts as Completed')
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status=Payout.STATUS_COMPLETED, paid_at=timezone.now())
        self.message_user(request, f'{updated} payout(s) marked completed.')
