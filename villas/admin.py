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
    list_display = ('slug', 'title_en', 'region', 'status', 'is_verified', 'base_price_idr', 'review_count')
    list_filter = ('status', 'region', 'is_verified', 'property_type', 'instant_book')
    search_fields = ('title_en', 'title_zh', 'slug')
    readonly_fields = ('created_at', 'updated_at', 'avg_rating', 'review_count', 'verified_at')
    inlines = [VillaPhotoInline, VillaAmenityInline]
    actions = ['approve_listings', 'pause_listings']

    @admin.action(description='Approve selected listings (set status → Published)')
    def approve_listings(self, request, queryset):
        updated = queryset.update(status=Villa.STATUS_PUBLISHED, is_verified=True)
        self.message_user(request, f'{updated} villa(s) approved and published.')

    @admin.action(description='Pause selected listings (set status → Paused)')
    def pause_listings(self, request, queryset):
        updated = queryset.update(status=Villa.STATUS_PAUSED)
        self.message_user(request, f'{updated} villa(s) paused.')


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
