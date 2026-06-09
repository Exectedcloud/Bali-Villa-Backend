from django.contrib import admin
from .models import Availability, Villa, VillaAmenity, VillaPhoto, Wishlist


class VillaPhotoInline(admin.TabularInline):
    model = VillaPhoto
    extra = 0
    fields = ('url', 'room_type', 'caption_en', 'order')
    ordering = ('order',)


class VillaAmenityInline(admin.TabularInline):
    model = VillaAmenity
    extra = 0
    fields = ('key', 'label_en', 'category', 'is_highlight')


@admin.register(Villa)
class VillaAdmin(admin.ModelAdmin):
    list_display = ('slug', 'title_en', 'region', 'status', 'is_verified', 'base_price_idr', 'review_count', 'created_at')
    list_filter = ('status', 'region', 'is_verified', 'property_type', 'instant_book')
    search_fields = ('title_en', 'title_zh', 'slug')
    readonly_fields = ('created_at', 'updated_at', 'avg_rating', 'review_count', 'verified_at', 'display_video')
    inlines = [VillaPhotoInline, VillaAmenityInline]
    actions = ['approve_listings', 'reject_listings', 'pause_listings']

    fieldsets = (
        ('Basic Info', {
            'fields': ('host', 'slug', 'title_en', 'title_zh', 'description_en', 'description_zh', 'property_type', 'status')
        }),
        ('Location', {
            'fields': ('region', 'city', 'address', 'location')
        }),
        ('Amenities & Pricing', {
            'fields': ('bedrooms', 'beds', 'bathrooms', 'max_guests', 'base_price_idr', 'base_price_cny', 'cleaning_fee_idr', 'instant_book', 'cancellation_policy')
        }),
        ('Media & Verification', {
            'fields': ('cover_photo_url', 'video_url', 'display_video', 'is_verified', 'verified_at', 'verified_by', 'rejection_reason')
        }),
        ('Stats', {
            'fields': ('avg_rating', 'review_count', 'tags', 'created_at', 'updated_at')
        }),
    )

    def display_video(self, obj):
        from django.utils.html import format_html
        if obj.video_url:
            return format_html(
                '<video src="{0}" controls style="max-height: 200px; border-radius: 8px;"></video><br>'
                '<a href="{0}" target="_blank">Open video in new tab</a>',
                obj.video_url
            )
        return "No video uploaded"
    display_video.short_description = "Video Preview"

    @admin.action(description='Approve selected listings (set status → Published)')
    def approve_listings(self, request, queryset):
        import datetime
        updated = queryset.update(
            status=Villa.STATUS_PUBLISHED,
            is_verified=True,
            verified_at=datetime.datetime.now(),
            verified_by=request.user
        )
        self.message_user(request, f'{updated} villa(s) approved and published.')

    @admin.action(description='Reject selected listings (set status → Draft)')
    def reject_listings(self, request, queryset):
        updated = queryset.update(status=Villa.STATUS_DRAFT)
        self.message_user(request, f'{updated} villa(s) sent back to Draft.')


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ('villa', 'date', 'status', 'price_override_idr')
    list_filter = ('status',)
    search_fields = ('villa__slug', 'villa__title_en')
    date_hierarchy = 'date'


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'villa', 'added_at')
    search_fields = ('user__email', 'villa__slug')
    readonly_fields = ('added_at',)
