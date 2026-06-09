import uuid
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Booking
from .serializers import BookingSerializer
from villas.models import Villa
from villas.serializers import ReviewSerializer
from reviews.models import Review
from payments.models import Payment
from services.translation import translate

# 12% of the guest's subtotal is retained as platform revenue;
# the host receives the remaining 88%.
PLATFORM_COMMISSION_RATE = Decimal('0.12')


class DraftBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        villa_slug = data.get('villaSlug')
        check_in_str = data.get('checkIn')
        check_out_str = data.get('checkOut')

        if not all([villa_slug, check_in_str, check_out_str]):
            return Response(
                {'error': 'villaSlug, checkIn, checkOut are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            villa = Villa.objects.get(slug=villa_slug, status=Villa.STATUS_PUBLISHED)
        except Villa.DoesNotExist:
            return Response({'error': 'Villa not found.'}, status=status.HTTP_404_NOT_FOUND)

        check_in = date.fromisoformat(check_in_str)
        check_out = date.fromisoformat(check_out_str)
        nights = (check_out - check_in).days
        if nights <= 0:
            return Response(
                {'error': 'checkOut must be after checkIn.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        reference = f'BV-{now.year}-{now.microsecond:05d}'
        subtotal_idr = villa.base_price_idr * nights
        subtotal_cny = villa.base_price_cny * nights
        # 3% payment processing fee (Airwallex / Stripe pass-through to guest).
        # When real payment processor is wired, replace the 3% constant with the
        # actual rate returned by the payment intent.
        _FEE = Decimal('0.03')
        payment_fee_idr = (subtotal_idr * _FEE).quantize(Decimal('1'))
        payment_fee_cny = (subtotal_cny * _FEE).quantize(Decimal('1'))

        booking = Booking.objects.create(
            reference=reference,
            guest=request.user,
            villa=villa,
            check_in=check_in,
            check_out=check_out,
            nights=nights,
            adults=int(data.get('adults', 1)),
            children=int(data.get('children', 0)),
            infants=int(data.get('infants', 0)),
            nightly_rate_idr=subtotal_idr,
            total_idr=subtotal_idr + payment_fee_idr,
            base_price_cny=subtotal_cny,
            total_cny=subtotal_cny + payment_fee_cny,
            payout_idr=subtotal_idr * (1 - PLATFORM_COMMISSION_RATE),
            status=Booking.STATUS_DRAFT,
            guest_note=data.get('guestNote', ''),
        )
        return Response({'booking': BookingSerializer(booking).data}, status=status.HTTP_201_CREATED)


class BookingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            Booking.objects
            .filter(guest=request.user)
            .select_related('villa__host__user', 'review')
            .prefetch_related('villa__photos', 'payments')
        )
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response({'bookings': BookingSerializer(qs, many=True).data})


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            booking = (
                Booking.objects
                .select_related('villa__host__user', 'review')
                .prefetch_related('villa__photos', 'payments')
                .get(pk=pk, guest=request.user)
            )
        except Booking.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'booking': BookingSerializer(booking).data})

    def patch(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, guest=request.user)
        except Booking.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if booking.status != Booking.STATUS_DRAFT:
            return Response(
                {'error': 'Only draft bookings can be updated.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = request.data
        if 'guestNote' in data:
            booking.guest_note = data['guestNote']
        if 'adults' in data:
            booking.adults = int(data['adults'])
        if 'children' in data:
            booking.children = int(data['children'])
        if 'infants' in data:
            booking.infants = int(data['infants'])
        booking.save()
        return Response({'booking': BookingSerializer(booking).data})


class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, guest=request.user)
        except Booking.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        cancellable = {
            Booking.STATUS_DRAFT,
            Booking.STATUS_PENDING_PAYMENT,
            Booking.STATUS_PENDING_APPROVAL,
            Booking.STATUS_CONFIRMED,
        }
        if booking.status not in cancellable:
            return Response(
                {'error': f'Cannot cancel a booking with status "{booking.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        booking.status = Booking.STATUS_CANCELLED
        booking.cancelled_at = timezone.now()
        booking.cancellation_reason = request.data.get('reason', '')
        booking.save()
        return Response({'booking': BookingSerializer(booking).data})


class BookingReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = (
                Booking.objects
                .select_related('villa', 'guest')
                .get(pk=pk, guest=request.user)
            )
        except Booking.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if booking.status != Booking.STATUS_COMPLETED:
            return Response(
                {'error': 'You can only review completed stays.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_review = Review.objects.filter(booking=booking).first()
        if existing_review:
            return Response(
                {'error': "You've already reviewed this stay."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rating = request.data.get('rating')
        text = (request.data.get('text') or '').strip()
        lang = request.data.get('lang', request.user.locale or 'zh')
        if lang not in ('zh', 'en'):
            lang = 'zh'

        if rating is None or not text:
            return Response(
                {'error': 'rating and text are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_lang = 'EN-US' if lang == 'zh' else 'ZH'
        translated_lang = 'en' if lang == 'zh' else 'zh'

        review = Review.objects.create(
            booking=booking,
            guest=request.user,
            villa=booking.villa,
            rating=Decimal(str(rating)),
            text_original=text,
            text_original_lang=lang,
            text_translated=translate(text, target_lang),
            text_translated_lang=translated_lang,
            rating_cleanliness=request.data.get('ratingCleanliness'),
            rating_accuracy=request.data.get('ratingAccuracy'),
            rating_checkin=request.data.get('ratingCheckin'),
            rating_communication=request.data.get('ratingCommunication'),
            rating_location=request.data.get('ratingLocation'),
            rating_value=request.data.get('ratingValue'),
        )

        villa = booking.villa
        all_ratings = list(Review.objects.filter(villa=villa, is_visible=True).values_list('rating', flat=True))
        villa.review_count = len(all_ratings)
        villa.avg_rating = sum(float(r) for r in all_ratings) / len(all_ratings) if all_ratings else 0
        villa.save(update_fields=['avg_rating', 'review_count'])

        return Response({'review': ReviewSerializer(review).data}, status=status.HTTP_201_CREATED)


class BookingConfirmView(APIView):
    """Stub — confirms booking and records a succeeded payment. No real payment processing."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = (
                Booking.objects
                .select_related('villa__host__user', 'review')
                .prefetch_related('villa__photos', 'payments')
                .get(pk=pk, guest=request.user)
            )
        except Booking.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if booking.status not in {Booking.STATUS_DRAFT, Booking.STATUS_PENDING_PAYMENT}:
            return Response(
                {'error': f'Cannot confirm a booking with status "{booking.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        method = request.data.get('paymentMethod', Payment.METHOD_WECHAT)
        valid = {Payment.METHOD_WECHAT, Payment.METHOD_ALIPAY, Payment.METHOD_UNIONPAY, Payment.METHOD_CARD}
        if method not in valid:
            return Response({'error': 'Invalid payment method.'}, status=status.HTTP_400_BAD_REQUEST)
        Payment.objects.create(
            booking=booking,
            awx_payment_intent_id=f'stub-{booking.reference}-{uuid.uuid4().hex[:8]}',
            method=method,
            status=Payment.STATUS_SUCCESS,
            amount_cny=booking.total_cny,
            amount_idr=booking.total_idr,
        )
        booking.status = Booking.STATUS_CONFIRMED
        booking.confirmed_at = timezone.now()
        booking.save()
        return Response({'booking': BookingSerializer(booking).data})


# ─── promo codes ──────────────────────────────────────────────────────────────

_PROMO_CODES = {
    'WELCOME10':      {'type': 'percent', 'value': Decimal('0.10')},
    'FIRSTBOOKING':   {'type': 'flat',    'value': Decimal('500000')},
    'CHINESENEWYEAR': {'type': 'percent', 'value': Decimal('0.15')},
}


class BookingPromoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, guest=request.user)
        except Booking.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        code = (request.data.get('code') or '').strip().upper()
        promo = _PROMO_CODES.get(code)

        if not promo:
            return Response({'valid': False, 'error': 'Invalid promo code.'})

        if promo['type'] == 'percent':
            discount_idr = (booking.total_idr * promo['value']).quantize(Decimal('1'))
        else:
            discount_idr = min(promo['value'], booking.total_idr)

        booking.promo_code = code
        booking.promo_discount_idr = discount_idr
        booking.save(update_fields=['promo_code', 'promo_discount_idr'])

        return Response({
            'valid': True,
            'discountIdr': int(discount_idr),
            'newTotalIdr': int(booking.total_idr - discount_idr),
        })


# ─── date modification ────────────────────────────────────────────────────────

_SERVICE_FEE_PCT = Decimal('0.12')
_TAX_PCT = Decimal('0.10')
_FALLBACK_FX = Decimal('0.000464')


class BookingModifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = (
                Booking.objects
                .select_related('villa')
                .get(pk=pk, guest=request.user)
            )
        except Booking.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if booking.status != Booking.STATUS_CONFIRMED:
            return Response(
                {'error': 'Only confirmed bookings can have their dates modified.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        check_in_str = request.data.get('checkIn')
        check_out_str = request.data.get('checkOut')
        if not check_in_str or not check_out_str:
            return Response({'error': 'checkIn and checkOut are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            check_in = date.fromisoformat(check_in_str)
            check_out = date.fromisoformat(check_out_str)
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        nights = (check_out - check_in).days
        if nights <= 0:
            return Response({'error': 'checkOut must be after checkIn.'}, status=status.HTTP_400_BAD_REQUEST)

        villa = booking.villa
        if nights < villa.min_nights:
            return Response({'error': f'Minimum stay is {villa.min_nights} nights.'}, status=status.HTTP_400_BAD_REQUEST)
        if nights > villa.max_nights:
            return Response({'error': f'Maximum stay is {villa.max_nights} nights.'}, status=status.HTTP_400_BAD_REQUEST)

        # Date conflict check (excluding current booking)
        has_conflict = Booking.objects.filter(
            villa=villa,
            status__in=[Booking.STATUS_CONFIRMED, Booking.STATUS_IN_HOUSE, Booking.STATUS_PENDING_PAYMENT],
            check_in__lt=check_out,
            check_out__gt=check_in,
        ).exclude(pk=pk).exists()
        if has_conflict:
            return Response({'error': 'Those dates are not available.'}, status=status.HTTP_400_BAD_REQUEST)

        # Recalculate price (same logic as CalculatePriceView)
        weekend_premium = Decimal(str(villa.weekend_premium_pct)) / Decimal('100')
        subtotal_idr = Decimal('0')
        current = check_in
        while current < check_out:
            rate = villa.base_price_idr
            if current.weekday() in (5, 6):
                rate = rate * (1 + weekend_premium)
            subtotal_idr += rate
            current += timedelta(days=1)

        cleaning_fee_idr = villa.cleaning_fee_idr
        service_fee_idr = (subtotal_idr * _SERVICE_FEE_PCT).quantize(Decimal('1'))
        tax_idr = ((subtotal_idr + service_fee_idr) * _TAX_PCT).quantize(Decimal('1'))
        total_idr = subtotal_idr + cleaning_fee_idr + service_fee_idr + tax_idr

        if villa.base_price_idr and villa.base_price_cny and villa.base_price_idr > 0:
            fx_rate = villa.base_price_cny / villa.base_price_idr
        else:
            fx_rate = _FALLBACK_FX
        total_cny = (total_idr * fx_rate).quantize(Decimal('1'))

        booking.check_in = check_in
        booking.check_out = check_out
        booking.nights = nights
        booking.nightly_rate_idr = subtotal_idr
        booking.total_idr = total_idr
        booking.base_price_cny = total_cny
        booking.total_cny = total_cny
        booking.payout_idr = total_idr * (1 - PLATFORM_COMMISSION_RATE)
        booking.save()

        booking_full = (
            Booking.objects
            .select_related('villa__host__user')
            .prefetch_related('villa__photos', 'payments')
            .get(pk=booking.pk)
        )
        return Response({'booking': BookingSerializer(booking_full).data})
