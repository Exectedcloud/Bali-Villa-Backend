from rest_framework import serializers
from .models import Booking


class VillaBriefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    titleEn = serializers.CharField(source='title_en')
    titleZh = serializers.CharField(source='title_zh')
    region = serializers.CharField()
    photos = serializers.SerializerMethodField()
    host = serializers.SerializerMethodField()

    def get_photos(self, obj):
        return list(obj.photos.order_by('order', 'created_at').values_list('url', flat=True)[:1])

    def get_host(self, obj):
        return {
            'id': obj.host.id,
            'displayName': obj.host.display_name,
            'avatarUrl': obj.host.user.avatar_url or '',
        }


class BookingSerializer(serializers.ModelSerializer):
    villaId = serializers.IntegerField(source='villa_id')
    villa = serializers.SerializerMethodField()
    checkIn = serializers.DateField(source='check_in')
    checkOut = serializers.DateField(source='check_out')
    guestNote = serializers.CharField(source='guest_note')
    totalCny = serializers.SerializerMethodField()
    totalIdr = serializers.SerializerMethodField()
    paymentMethod = serializers.SerializerMethodField()
    paidAt = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at')
    cancelledAt = serializers.SerializerMethodField()
    cancellationReason = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'reference', 'villaId', 'villa', 'status', 'checkIn', 'checkOut', 'nights',
            'adults', 'children', 'infants', 'guestNote',
            'totalCny', 'totalIdr', 'paymentMethod', 'paidAt',
            'createdAt', 'cancelledAt', 'cancellationReason',
        ]

    _METHOD_MAP = {
        'wechat_pay': 'wechat',
        'alipay': 'alipay',
        'unionpay': 'unionpay',
        'card': 'card',
    }

    def _paid_payment(self, obj):
        return obj.payments.filter(status__in=['success', 'refunded', 'partially_refunded']).first()

    def get_villa(self, obj):
        try:
            return VillaBriefSerializer(obj.villa).data
        except Exception:
            return None

    def get_totalCny(self, obj):
        return int(obj.total_cny)

    def get_totalIdr(self, obj):
        return int(obj.total_idr)

    def get_paymentMethod(self, obj):
        p = self._paid_payment(obj)
        return self._METHOD_MAP.get(p.method) if p else None

    def get_paidAt(self, obj):
        p = self._paid_payment(obj)
        return p.created_at.isoformat() if p else None

    def get_cancelledAt(self, obj):
        return obj.cancelled_at.isoformat() if obj.cancelled_at else None

    def get_cancellationReason(self, obj):
        return obj.cancellation_reason or None
