from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference', 'guest', 'villa', 'check_in', 'check_out', 'nights', 'status', 'total_cny')
    list_filter = ('status', 'check_in')
    search_fields = ('reference', 'guest__email', 'villa__slug')
    readonly_fields = (
        'reference', 'created_at', 'updated_at',
        'confirmed_at', 'cancelled_at', 'host_responded_at',
    )
    fieldsets = (
        ('Booking', {'fields': ('reference', 'guest', 'villa', 'status')}),
        ('Dates & Guests', {'fields': ('check_in', 'check_out', 'nights', 'adults', 'children', 'infants')}),
        ('Pricing (IDR)', {'fields': ('nightly_rate_idr', 'cleaning_fee_idr', 'service_fee_idr', 'tax_idr', 'total_idr', 'payout_idr')}),
        ('Pricing (CNY)', {'fields': ('base_price_cny', 'cleaning_fee_cny', 'service_fee_cny', 'tax_cny', 'total_cny')}),
        ('FX', {'fields': ('mid_rate', 'awx_rate', 'client_rate', 'fx_quote_id', 'fx_quote_expires_at')}),
        ('Notes', {'fields': ('guest_note', 'host_note', 'special_requests', 'additional_guests')}),
        ('Promo', {'fields': ('promo_code', 'promo_discount_idr')}),
        ('Timestamps', {'fields': ('created_at', 'confirmed_at', 'cancelled_at', 'host_responded_at', 'updated_at')}),
    )
    actions = ['mark_confirmed', 'mark_cancelled']

    @admin.action(description='Mark selected bookings as Confirmed')
    def mark_confirmed(self, request, queryset):
        updated = queryset.update(status=Booking.STATUS_CONFIRMED)
        self.message_user(request, f'{updated} booking(s) confirmed.')

    @admin.action(description='Mark selected bookings as Cancelled')
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status=Booking.STATUS_CANCELLED)
        self.message_user(request, f'{updated} booking(s) cancelled.')
