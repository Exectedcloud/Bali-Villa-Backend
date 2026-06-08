import calendar as _cal
import datetime
import uuid
from decimal import Decimal
from django.utils.text import slugify
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import HostProfile
from users.permissions import HasHostRole
from services.translation import translate
from .models import Villa, VillaPhoto, VillaAmenity, Availability
from .serializers import VillaSerializer


def _auto_translate_villa(villa: Villa) -> None:
    """Fill in the missing language for title and description, save if changed."""
    changed = False
    if villa.title_en and not villa.title_zh:
        villa.title_zh = translate(villa.title_en, 'ZH', 'EN')
        changed = True
    elif villa.title_zh and not villa.title_en:
        villa.title_en = translate(villa.title_zh, 'EN-US', 'ZH')
        changed = True
    if villa.description_en and not villa.description_zh:
        villa.description_zh = translate(villa.description_en, 'ZH', 'EN')
        changed = True
    elif villa.description_zh and not villa.description_en:
        villa.description_en = translate(villa.description_zh, 'EN-US', 'ZH')
        changed = True
    if changed:
        villa.save(update_fields=['title_zh', 'title_en', 'description_zh', 'description_en'])


def _make_slug(base: str) -> str:
    slug = slugify(base)[:100] or f'villa-{uuid.uuid4().hex[:8]}'
    if not Villa.objects.filter(slug=slug).exists():
        return slug
    for i in range(1, 100):
        candidate = f'{slug}-{i}'
        if not Villa.objects.filter(slug=candidate).exists():
            return candidate
    return f'{slug}-{uuid.uuid4().hex[:8]}'


class HostVillaListView(APIView):
    permission_classes = [HasHostRole]

    def _get_host(self, user):
        try:
            return user.host_profile
        except HostProfile.DoesNotExist:
            return None

    def get(self, request):
        host = self._get_host(request.user)
        if not host:
            return Response({'error': 'Not a host account.'}, status=status.HTTP_403_FORBIDDEN)
        villas = (
            Villa.objects
            .filter(host=host)
            .select_related('host__user')
            .prefetch_related('photos', 'amenities')
        )
        return Response({'villas': VillaSerializer(villas, many=True).data})

    def post(self, request):
        host = self._get_host(request.user)
        if not host:
            return Response({'error': 'Not a host account.'}, status=status.HTTP_403_FORBIDDEN)

        d = request.data
        title_en = (d.get('title') or d.get('propertyName') or '').strip()
        if not title_en:
            return Response({'error': 'title is required.'}, status=status.HTTP_400_BAD_REQUEST)

        base_price_idr = d.get('basePriceIdr')
        if not base_price_idr:
            return Response({'error': 'basePriceIdr is required.'}, status=status.HTTP_400_BAD_REQUEST)

        villa = Villa.objects.create(
            host=host,
            slug=_make_slug(title_en),
            title_en=title_en,
            title_zh=d.get('titleZh') or '',
            description_en=d.get('description') or '',
            description_zh=d.get('descriptionZh') or '',
            property_type=d.get('propertyType') or Villa.TYPE_VILLA,
            region=d.get('region') or '',
            city=d.get('city') or '',
            address=d.get('address') or '',
            bedrooms=int(d.get('bedrooms') or 1),
            beds=int(d.get('beds') or 1),
            bathrooms=float(d.get('bathrooms') or 1),
            max_guests=int(d.get('guests') or 2),
            min_nights=int(d.get('minNights') or 1),
            max_nights=int(d.get('maxNights') or 30),
            base_price_idr=int(base_price_idr),
            base_price_cny=0,
            cleaning_fee_idr=int(d.get('cleaningFee') or 0),
            instant_book=bool(d.get('instantBook')),
            cancellation_policy=d.get('cancellationPolicy') or Villa.POLICY_MODERATE,
            highlights=d.get('highlights') or [],
            house_rules=d.get('houseRules') or [],
            check_in_from=d.get('checkInFrom') or None,
            check_in_until=d.get('checkInUntil') or None,
            check_out_by=d.get('checkOut') or None,
            weekend_premium_pct=int(d.get('weekendPremium') or 0),
            status=Villa.STATUS_PENDING_REVIEW,
        )

        photos = d.get('photos') or []
        for i, p in enumerate(photos):
            url = p.get('url') if isinstance(p, dict) else p
            if url:
                VillaPhoto.objects.create(
                    villa=villa,
                    url=url,
                    room_type=p.get('label', '') if isinstance(p, dict) else '',
                    order=i,
                )

        amenities = d.get('amenities') or []
        for a in amenities:
            key = a.get('key') if isinstance(a, dict) else a
            if key:
                VillaAmenity.objects.get_or_create(
                    villa=villa,
                    key=key,
                    defaults={
                        'category': a.get('category', 'essentials') if isinstance(a, dict) else 'essentials',
                    },
                )

        if d.get('bankHolder') or d.get('bankName') or d.get('bankAccount'):
            host.payout_bank = {
                'account_name': d.get('bankHolder') or '',
                'bank_name': d.get('bankName') or '',
                'account_number': d.get('bankAccount') or '',
                'swift_code': d.get('swiftCode') or '',
                'payout_currency': d.get('payoutCurrency') or 'IDR',
            }
            host.save(update_fields=['payout_bank'])

        _auto_translate_villa(villa)

        villa_full = (
            Villa.objects
            .select_related('host__user')
            .prefetch_related('photos', 'amenities')
            .get(pk=villa.pk)
        )
        return Response({'villa': VillaSerializer(villa_full).data}, status=status.HTTP_201_CREATED)


class HostVillaDetailView(APIView):
    permission_classes = [HasHostRole]

    def _get_villa(self, request, pk):
        host = getattr(request.user, 'host_profile', None)
        if not host:
            return None, Response({'error': 'Not a host account.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            villa = Villa.objects.select_related('host__user').prefetch_related('photos', 'amenities').get(pk=pk, host=host)
        except Villa.DoesNotExist:
            return None, Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return villa, None

    def get(self, request, pk):
        villa, err = self._get_villa(request, pk)
        if err:
            return err
        return Response({'villa': VillaSerializer(villa).data})

    def patch(self, request, pk):
        villa, err = self._get_villa(request, pk)
        if err:
            return err
        d = request.data
        update_fields = []
        for field, key in [
            ('base_price_idr', 'basePriceIdr'),
            ('cleaning_fee_idr', 'cleaningFee'),
            ('min_nights', 'minNights'),
            ('max_nights', 'maxNights'),
            ('weekend_premium_pct', 'weekendPremium'),
            ('cancellation_policy', 'cancellationPolicy'),
            ('instant_book', 'instantBook'),
        ]:
            if key in d:
                setattr(villa, field, d[key])
                update_fields.append(field)
        if 'houseRules' in d:
            villa.house_rules = d['houseRules']
            update_fields.append('house_rules')
        if 'status' in d and d['status'] in (Villa.STATUS_PUBLISHED, Villa.STATUS_PAUSED):
            villa.status = d['status']
            update_fields.append('status')
        if update_fields:
            villa.save(update_fields=update_fields)
        villa.refresh_from_db()
        villa_full = Villa.objects.select_related('host__user').prefetch_related('photos', 'amenities').get(pk=villa.pk)
        return Response({'villa': VillaSerializer(villa_full).data})


# ─── calendar helpers ─────────────────────────────────────────────────────────

def _get_host_or_403(user):
    try:
        return user.host_profile, None
    except HostProfile.DoesNotExist:
        from rest_framework.response import Response as R
        return None, R({'error': 'Not a host account.'}, status=403)


def _get_host_villa(host, villa_id):
    try:
        return Villa.objects.get(pk=villa_id, host=host), None
    except Villa.DoesNotExist:
        from rest_framework.response import Response as R
        return None, R({'error': 'Villa not found.'}, status=404)


# ─── calendar views ───────────────────────────────────────────────────────────

class HostCalendarView(APIView):
    """GET /host/calendar/?villaIds=1,2&month=2026-06"""
    permission_classes = [HasHostRole]

    def get(self, request):
        host, err = _get_host_or_403(request.user)
        if err:
            return err

        month_str = request.query_params.get('month', '')
        if not month_str:
            today = datetime.date.today()
            month_str = today.strftime('%Y-%m')
        try:
            year, month = (int(p) for p in month_str.split('-'))
            start_date = datetime.date(year, month, 1)
            last_day = _cal.monthrange(year, month)[1]
            end_date = datetime.date(year, month, last_day)
        except (ValueError, AttributeError):
            return Response(
                {'error': 'Invalid month format. Use YYYY-MM.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        villa_ids_str = request.query_params.get('villaIds', '')
        if villa_ids_str:
            try:
                villa_ids = [int(x.strip()) for x in villa_ids_str.split(',') if x.strip()]
            except ValueError:
                return Response({'error': 'Invalid villaIds.'}, status=status.HTTP_400_BAD_REQUEST)
            villas = Villa.objects.filter(pk__in=villa_ids, host=host)
        else:
            villas = Villa.objects.filter(host=host)

        from bookings.models import Booking
        result = {}
        for villa in villas:
            date_map = {}

            # Availability records (blocks + price overrides)
            for a in Availability.objects.filter(villa=villa, date__range=(start_date, end_date)):
                date_map[a.date.isoformat()] = {
                    'status': a.status,
                    'priceOverrideIdr': int(a.price_override_idr) if a.price_override_idr else None,
                    'bookingId': None,
                }

            # Confirmed/in-house bookings overlay (take priority over availability records)
            bookings = Booking.objects.filter(
                villa=villa,
                status__in=[Booking.STATUS_CONFIRMED, Booking.STATUS_IN_HOUSE, Booking.STATUS_PENDING_PAYMENT],
                check_in__lt=end_date + datetime.timedelta(days=1),
                check_out__gt=start_date,
            )
            for booking in bookings:
                cur = max(booking.check_in, start_date)
                b_end = min(booking.check_out, end_date + datetime.timedelta(days=1))
                while cur < b_end:
                    date_map[cur.isoformat()] = {
                        'status': 'booked',
                        'priceOverrideIdr': None,
                        'bookingId': booking.id,
                    }
                    cur += datetime.timedelta(days=1)

            result[str(villa.id)] = date_map

        return Response(result)


class HostCalendarBlockView(APIView):
    """POST /host/calendar/block/ — block dates; DELETE — unblock dates."""
    permission_classes = [HasHostRole]

    def post(self, request):
        host, err = _get_host_or_403(request.user)
        if err:
            return err

        villa_id = request.data.get('villaId')
        dates = request.data.get('dates') or []
        reason = request.data.get('reason', '')

        if not villa_id or not dates:
            return Response(
                {'error': 'villaId and dates are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        villa, err = _get_host_villa(host, villa_id)
        if err:
            return err

        try:
            date_objects = [datetime.date.fromisoformat(d) for d in dates]
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        # Refuse if any date is already booked
        booked = Availability.objects.filter(
            villa=villa, date__in=date_objects, status=Availability.STATUS_BOOKED
        )
        if booked.exists():
            return Response(
                {'error': 'Cannot block dates that are already booked.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for d in date_objects:
            Availability.objects.update_or_create(
                villa=villa, date=d,
                defaults={'status': Availability.STATUS_BLOCKED, 'note': reason},
            )

        return Response({'blocked': len(date_objects), 'dates': dates})

    def delete(self, request):
        host, err = _get_host_or_403(request.user)
        if err:
            return err

        villa_id = request.data.get('villaId')
        dates = request.data.get('dates') or []

        if not villa_id or not dates:
            return Response(
                {'error': 'villaId and dates are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        villa, err = _get_host_villa(host, villa_id)
        if err:
            return err

        try:
            date_objects = [datetime.date.fromisoformat(d) for d in dates]
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        deleted, _ = Availability.objects.filter(
            villa=villa, date__in=date_objects, status=Availability.STATUS_BLOCKED
        ).delete()
        return Response({'unblocked': deleted})


class HostCalendarPriceView(APIView):
    """POST /host/calendar/price/ — set price override for specific dates."""
    permission_classes = [HasHostRole]

    def post(self, request):
        host, err = _get_host_or_403(request.user)
        if err:
            return err

        villa_id = request.data.get('villaId')
        dates = request.data.get('dates') or []
        price_idr = request.data.get('priceIdr')

        if not villa_id or not dates or price_idr is None:
            return Response(
                {'error': 'villaId, dates, and priceIdr are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        villa, err = _get_host_villa(host, villa_id)
        if err:
            return err

        try:
            date_objects = [datetime.date.fromisoformat(d) for d in dates]
            price = Decimal(str(price_idr))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid date or priceIdr.'}, status=status.HTTP_400_BAD_REQUEST)

        for d in date_objects:
            Availability.objects.update_or_create(
                villa=villa, date=d,
                defaults={'price_override_idr': price},
            )

        return Response({'updated': len(date_objects), 'priceIdr': int(price)})
