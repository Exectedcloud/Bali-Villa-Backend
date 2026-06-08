import datetime
from datetime import timedelta
from decimal import Decimal
from django.core.cache import cache
from django.db.models import Avg, Count
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from services.translation import translate
from .models import Villa, Availability, Wishlist
from .serializers import VillaSerializer, VillaDetailSerializer, ReviewSerializer
from reviews.models import Review


class VillaListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = (
            Villa.objects
            .filter(status=Villa.STATUS_PUBLISHED)
            .select_related('host__user')
            .prefetch_related('photos', 'amenities')
        )
        if request.query_params.get('featured') == 'true':
            qs = qs.filter(tags__icontains='balivilla_select')
        region = request.query_params.get('region')
        if region:
            qs = qs.filter(region__iexact=region)
        bedrooms = request.query_params.get('bedrooms')
        if bedrooms:
            qs = qs.filter(bedrooms__gte=int(bedrooms))
        guests = request.query_params.get('guests')
        if guests:
            qs = qs.filter(max_guests__gte=int(guests))
        min_price = request.query_params.get('minPriceIdr')
        if min_price:
            qs = qs.filter(base_price_idr__gte=int(min_price))
        max_price = request.query_params.get('maxPriceIdr')
        if max_price:
            qs = qs.filter(base_price_idr__lte=int(max_price))
        total = qs.count()
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 24))
        offset = (page - 1) * page_size
        villas = qs[offset:offset + page_size]
        return Response({
            'villas': VillaSerializer(villas, many=True).data,
            'total': total,
            'page': page,
            'pageSize': page_size,
        })


class VillaDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            villa = (
                Villa.objects
                .select_related('host__user')
                .prefetch_related('photos', 'amenities')
                .get(slug=slug, status=Villa.STATUS_PUBLISHED)
            )
        except Villa.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'villa': VillaDetailSerializer(villa).data})


class VillaReviewsView(APIView):
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request, pk):
        reviews = Review.objects.filter(villa_id=pk, is_visible=True).select_related('guest')
        return Response({'reviews': ReviewSerializer(reviews, many=True).data})

    def post(self, request, pk):
        try:
            villa = Villa.objects.get(pk=pk, status=Villa.STATUS_PUBLISHED)
        except Villa.DoesNotExist:
            return Response({'error': 'Villa not found.'}, status=status.HTTP_404_NOT_FOUND)

        rating = request.data.get('rating')
        text = (request.data.get('text') or '').strip()
        lang = request.data.get('lang', 'zh')
        if lang not in ('zh', 'en'):
            lang = 'zh'

        if rating is None or not text:
            return Response({'error': 'rating and text are required.'}, status=status.HTTP_400_BAD_REQUEST)

        target_lang = 'EN-US' if lang == 'zh' else 'ZH'
        translated_lang = 'en' if lang == 'zh' else 'zh'

        review = Review.objects.create(
            guest=request.user,
            villa=villa,
            rating=rating,
            text_original=text,
            text_original_lang=lang,
            text_translated=translate(text, target_lang),
            text_translated_lang=translated_lang,
            rating_cleanliness=request.data.get('cleanliness'),
            rating_accuracy=request.data.get('accuracy'),
            rating_checkin=request.data.get('checkin'),
            rating_location=request.data.get('location'),
            rating_value=request.data.get('value'),
            rating_communication=request.data.get('communication'),
        )

        all_ratings = list(Review.objects.filter(villa=villa, is_visible=True).values_list('rating', flat=True))
        villa.review_count = len(all_ratings)
        villa.avg_rating = sum(float(r) for r in all_ratings) / len(all_ratings) if all_ratings else 0
        villa.save(update_fields=['avg_rating', 'review_count'])

        return Response({'review': ReviewSerializer(review).data}, status=status.HTTP_201_CREATED)


class VillaAvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        today = datetime.date.today()
        start_str = request.query_params.get('start')
        end_str = request.query_params.get('end')
        start = datetime.date.fromisoformat(start_str) if start_str else today
        end = datetime.date.fromisoformat(end_str) if end_str else today + datetime.timedelta(days=90)
        blocked = {
            a.date: a.status
            for a in Availability.objects.filter(villa_id=pk, date__range=(start, end))
        }
        result, current = [], start
        while current <= end:
            result.append({'date': current.isoformat(), 'status': blocked.get(current, 'available')})
            current += datetime.timedelta(days=1)
        return Response({'availability': result})


class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        villa_ids = Wishlist.objects.filter(user=request.user).values_list('villa_id', flat=True)
        villas = (
            Villa.objects
            .filter(id__in=villa_ids, status=Villa.STATUS_PUBLISHED)
            .select_related('host__user')
            .prefetch_related('photos', 'amenities')
        )
        return Response({'villas': VillaSerializer(villas, many=True).data})

    def post(self, request):
        villa_id = request.data.get('villaId')
        if not villa_id:
            return Response({'error': 'villaId required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            villa = Villa.objects.get(pk=villa_id, status=Villa.STATUS_PUBLISHED)
        except Villa.DoesNotExist:
            return Response({'error': 'Villa not found.'}, status=status.HTTP_404_NOT_FOUND)
        Wishlist.objects.get_or_create(user=request.user, villa=villa)
        return Response({'detail': 'Added to wishlist.'}, status=status.HTTP_201_CREATED)


class WishlistVillaView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, villa_id):
        Wishlist.objects.filter(user=request.user, villa_id=villa_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VillaSimilarView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            villa = Villa.objects.get(pk=pk, status=Villa.STATUS_PUBLISHED)
        except Villa.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        similar = (
            Villa.objects
            .filter(status=Villa.STATUS_PUBLISHED, region=villa.region)
            .exclude(pk=pk)
            .select_related('host__user')
            .prefetch_related('photos', 'amenities')
            .order_by('-avg_rating')[:4]
        )
        return Response(VillaSerializer(similar, many=True).data)


class RegionStatsView(APIView):
    permission_classes = [AllowAny]
    _CACHE_KEY = 'region_stats'
    _CACHE_TTL = 60 * 60  # 1 hour

    def get(self, request):
        cached = cache.get(self._CACHE_KEY)
        if cached is not None:
            return Response(cached)

        rows = (
            Villa.objects
            .filter(status=Villa.STATUS_PUBLISHED)
            .exclude(region='')
            .values('region')
            .annotate(villaCount=Count('id'), avgPriceIdr=Avg('base_price_idr'), avgPriceCny=Avg('base_price_cny'))
            .order_by('region')
        )
        result = [
            {
                'region': r['region'],
                'villaCount': r['villaCount'],
                'avgPriceIdr': int(r['avgPriceIdr']) if r['avgPriceIdr'] else 0,
                'avgPriceCny': int(r['avgPriceCny']) if r['avgPriceCny'] else 0,
            }
            for r in rows
        ]
        cache.set(self._CACHE_KEY, result, self._CACHE_TTL)
        return Response(result)


class VillaFeaturedView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        villas = (
            Villa.objects
            .filter(status=Villa.STATUS_PUBLISHED, tags__icontains='balivilla_select')
            .select_related('host__user')
            .prefetch_related('photos', 'amenities')
            .order_by('-avg_rating')[:10]
        )
        return Response(VillaSerializer(villas, many=True).data)


class CalculatePriceView(APIView):
    permission_classes = [AllowAny]

    _SERVICE_FEE_PCT = Decimal('0.12')
    _TAX_PCT = Decimal('0.10')
    _FALLBACK_FX = Decimal('0.000464')  # IDR → CNY fallback

    def post(self, request, pk):
        try:
            villa = Villa.objects.get(pk=pk, status=Villa.STATUS_PUBLISHED)
        except Villa.DoesNotExist:
            return Response({'error': 'Villa not found.'}, status=status.HTTP_404_NOT_FOUND)

        check_in_str = request.data.get('checkIn')
        check_out_str = request.data.get('checkOut')
        guests_raw = request.data.get('guests', 1)

        if not check_in_str or not check_out_str:
            return Response(
                {'error': 'checkIn and checkOut are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            check_in = datetime.date.fromisoformat(check_in_str)
            check_out = datetime.date.fromisoformat(check_out_str)
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nights = (check_out - check_in).days
        if nights <= 0:
            return Response({'error': 'checkOut must be after checkIn.'}, status=status.HTTP_400_BAD_REQUEST)
        if nights < villa.min_nights:
            return Response(
                {'error': f'Minimum stay is {villa.min_nights} nights.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if nights > villa.max_nights:
            return Response(
                {'error': f'Maximum stay is {villa.max_nights} nights.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            guests = int(guests_raw)
        except (ValueError, TypeError):
            return Response({'error': 'guests must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
        if guests > villa.max_guests:
            return Response(
                {'error': f'Maximum guests for this villa is {villa.max_guests}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Nightly subtotal with weekend premium
        weekend_premium = Decimal(str(villa.weekend_premium_pct)) / Decimal('100')
        subtotal_idr = Decimal('0')
        current = check_in
        while current < check_out:
            rate = villa.base_price_idr
            if current.weekday() in (5, 6):  # Sat, Sun
                rate = rate * (1 + weekend_premium)
            subtotal_idr += rate
            current += timedelta(days=1)

        cleaning_fee_idr = villa.cleaning_fee_idr
        service_fee_idr = (subtotal_idr * self._SERVICE_FEE_PCT).quantize(Decimal('1'))
        tax_idr = ((subtotal_idr + service_fee_idr) * self._TAX_PCT).quantize(Decimal('1'))
        total_idr = subtotal_idr + cleaning_fee_idr + service_fee_idr + tax_idr

        # FX rate derived from villa's cached CNY price; fall back to constant
        if villa.base_price_idr and villa.base_price_cny and villa.base_price_idr > 0:
            fx_rate = villa.base_price_cny / villa.base_price_idr
        else:
            fx_rate = self._FALLBACK_FX

        total_cny = (total_idr * fx_rate).quantize(Decimal('1'))

        return Response({
            'nightlyRateIdr': int(villa.base_price_idr),
            'nights': nights,
            'subtotalIdr': int(subtotal_idr),
            'cleaningFeeIdr': int(cleaning_fee_idr),
            'serviceFeeIdr': int(service_fee_idr),
            'taxIdr': int(tax_idr),
            'totalIdr': int(total_idr),
            'totalCny': int(total_cny),
            'currency': 'IDR',
        })
