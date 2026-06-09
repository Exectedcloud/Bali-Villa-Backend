from rest_framework import serializers
from .models import Villa, Availability
from users.models import HostProfile
from reviews.models import Review


class HostBriefSerializer(serializers.ModelSerializer):
    displayName = serializers.CharField(source='display_name')
    avatarUrl = serializers.SerializerMethodField()
    hostingSince = serializers.IntegerField(source='hosting_since')
    responseRate = serializers.SerializerMethodField()

    class Meta:
        model = HostProfile
        fields = ['id', 'displayName', 'avatarUrl', 'hostingSince', 'responseRate', 'languages', 'bio']

    def get_avatarUrl(self, obj):
        return obj.user.avatar_url or ''

    def get_responseRate(self, obj):
        return int(float(obj.response_rate)) if obj.response_rate else 0


class VillaSerializer(serializers.ModelSerializer):
    titleEn = serializers.CharField(source='title_en')
    titleZh = serializers.CharField(source='title_zh')
    maxGuests = serializers.IntegerField(source='max_guests')
    instantBook = serializers.BooleanField(source='instant_book')
    bathrooms = serializers.SerializerMethodField()
    basePriceIdr = serializers.SerializerMethodField()
    basePriceCny = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    reviewCount = serializers.IntegerField(source='review_count')
    photos = serializers.SerializerMethodField()
    amenities = serializers.SerializerMethodField()
    highlights = serializers.JSONField()
    badges = serializers.JSONField(source='tags')
    hostId = serializers.IntegerField(source='host_id')
    videoUrl = serializers.CharField(source='video_url', read_only=True)

    class Meta:
        model = Villa
        fields = [
            'id', 'slug', 'status', 'titleEn', 'titleZh', 'location', 'region',
            'bedrooms', 'beds', 'bathrooms', 'maxGuests', 'instantBook',
            'basePriceIdr', 'basePriceCny', 'rating', 'reviewCount',
            'photos', 'amenities', 'highlights', 'badges', 'hostId', 'videoUrl',
        ]

    def get_bathrooms(self, obj):
        v = float(obj.bathrooms)
        return int(v) if v == int(v) else v

    def get_basePriceIdr(self, obj):
        return int(obj.base_price_idr)

    # Fallback rate used when the Celery FX task hasn't populated base_price_cny yet.
    # ~2155 IDR per 1 CNY matches the live rate used in seeded data.
    _IDR_PER_CNY_FALLBACK = 2155

    def get_basePriceCny(self, obj):
        if obj.base_price_cny and obj.base_price_cny > 0:
            return int(obj.base_price_cny)
        return round(int(obj.base_price_idr) / self._IDR_PER_CNY_FALLBACK)

    def get_rating(self, obj):
        return float(obj.avg_rating)

    def get_photos(self, obj):
        return list(obj.photos.order_by('order', 'created_at').values_list('url', flat=True))

    def get_amenities(self, obj):
        return list(obj.amenities.filter(available=True).values_list('key', flat=True))


class VillaDetailSerializer(VillaSerializer):
    descriptionEn = serializers.CharField(source='description_en')
    descriptionZh = serializers.CharField(source='description_zh')
    host = serializers.SerializerMethodField()

    class Meta(VillaSerializer.Meta):
        fields = VillaSerializer.Meta.fields + ['descriptionEn', 'descriptionZh', 'host']

    def get_host(self, obj):
        return HostBriefSerializer(obj.host).data


class HostVillaSerializer(VillaDetailSerializer):
    """
    VillaDetailSerializer plus host-private fields needed by the listing edit page.
    Not exposed on public villa endpoints.
    """
    cleaningFeeIdr = serializers.SerializerMethodField()
    weekendPremiumPct = serializers.IntegerField(source='weekend_premium_pct')
    minNights = serializers.IntegerField(source='min_nights')
    maxNights = serializers.IntegerField(source='max_nights')
    cancellationPolicy = serializers.CharField(source='cancellation_policy')
    houseRules = serializers.JSONField(source='house_rules')

    class Meta(VillaDetailSerializer.Meta):
        fields = VillaDetailSerializer.Meta.fields + [
            'cleaningFeeIdr', 'weekendPremiumPct', 'minNights', 'maxNights',
            'cancellationPolicy', 'houseRules',
        ]

    def get_cleaningFeeIdr(self, obj):
        return int(obj.cleaning_fee_idr)

    def get_photos(self, obj):
        return [
            {'id': p.id, 'url': p.url, 'order': p.order, 'roomType': p.room_type}
            for p in obj.photos.order_by('order', 'created_at')
        ]


class ReviewSerializer(serializers.ModelSerializer):
    villaId = serializers.IntegerField(source='villa_id')
    guestName = serializers.SerializerMethodField()
    guestAvatarUrl = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    textEn = serializers.SerializerMethodField()
    textZh = serializers.SerializerMethodField()
    cleanliness = serializers.SerializerMethodField()
    accuracy = serializers.SerializerMethodField()
    checkin = serializers.SerializerMethodField()
    communication = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'villaId', 'guestName', 'guestAvatarUrl',
            'rating', 'date', 'textEn', 'textZh',
            'cleanliness', 'accuracy', 'checkin', 'communication', 'location', 'value',
        ]

    def get_guestName(self, obj):
        name = f'{obj.guest.first_name} {obj.guest.last_name}'.strip()
        return name or obj.guest.email

    def get_guestAvatarUrl(self, obj):
        return obj.guest.avatar_url or ''

    def get_rating(self, obj):
        return float(obj.rating)

    def get_date(self, obj):
        return obj.published_at.strftime('%Y-%m-%d')

    def _f(self, val):
        return float(val) if val is not None else None

    def get_textEn(self, obj):
        return obj.text_original if obj.text_original_lang == 'en' else obj.text_translated

    def get_textZh(self, obj):
        return obj.text_original if obj.text_original_lang == 'zh' else obj.text_translated

    def get_cleanliness(self, obj):
        return self._f(obj.rating_cleanliness)

    def get_accuracy(self, obj):
        return self._f(obj.rating_accuracy)

    def get_checkin(self, obj):
        return self._f(obj.rating_checkin)

    def get_communication(self, obj):
        return self._f(obj.rating_communication)

    def get_location(self, obj):
        return self._f(obj.rating_location)

    def get_value(self, obj):
        return self._f(obj.rating_value)
