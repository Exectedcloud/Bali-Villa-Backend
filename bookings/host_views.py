from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import HostProfile
from users.permissions import HasHostRole
from .models import Booking
from .serializers import BookingSerializer


class HostBookingSerializer(BookingSerializer):
    guestName = serializers.SerializerMethodField()
    guestAvatarUrl = serializers.SerializerMethodField()
    payoutIdr = serializers.SerializerMethodField()
    guestEmail = serializers.SerializerMethodField()
    guestPhone = serializers.SerializerMethodField()

    class Meta(BookingSerializer.Meta):
        fields = BookingSerializer.Meta.fields + [
            'guestName', 'guestAvatarUrl', 'payoutIdr', 'guestEmail', 'guestPhone',
        ]

    def get_guestName(self, obj):
        return f'{obj.guest.first_name} {obj.guest.last_name}'.strip() or obj.guest.email

    def get_guestAvatarUrl(self, obj):
        return obj.guest.avatar_url or ''

    def get_payoutIdr(self, obj):
        return int(obj.payout_idr)

    def _contact_visible(self, obj) -> bool:
        return obj.status in {
            Booking.STATUS_CONFIRMED,
            Booking.STATUS_IN_HOUSE,
            Booking.STATUS_COMPLETED,
        }

    def get_guestEmail(self, obj):
        return obj.guest.email if self._contact_visible(obj) else None

    def get_guestPhone(self, obj):
        return obj.guest.phone if self._contact_visible(obj) else None


class HostBookingDetailView(APIView):
    permission_classes = [HasHostRole]

    def get(self, request, pk):
        try:
            host = request.user.host_profile
        except HostProfile.DoesNotExist:
            return Response({'error': 'Not a host account.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            booking = (
                Booking.objects
                .select_related('villa__host__user', 'guest')
                .prefetch_related('villa__photos', 'payments')
                .get(pk=pk, villa__host=host)
            )
        except Booking.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'booking': HostBookingSerializer(booking).data})


class HostBookingListView(APIView):
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
        qs = (
            Booking.objects
            .filter(villa__host=host)
            .select_related('villa__host__user', 'guest')
            .prefetch_related('villa__photos', 'payments')
            .order_by('-created_at')
        )
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response({'bookings': HostBookingSerializer(qs, many=True).data})


class HostBookingApproveView(APIView):
    permission_classes = [HasHostRole]

    def post(self, request, pk):
        try:
            host = request.user.host_profile
        except HostProfile.DoesNotExist:
            return Response({'error': 'Not a host account.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            booking = (
                Booking.objects
                .select_related('villa__host__user', 'guest')
                .prefetch_related('villa__photos', 'payments')
                .get(pk=pk, villa__host=host)
            )
        except Booking.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if booking.status != Booking.STATUS_PENDING_APPROVAL:
            return Response(
                {'error': f'Cannot approve a booking with status "{booking.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        booking.status = Booking.STATUS_CONFIRMED
        booking.confirmed_at = timezone.now()
        booking.host_responded_at = timezone.now()
        booking.save()
        return Response({'booking': HostBookingSerializer(booking).data})


class HostBookingDeclineView(APIView):
    permission_classes = [HasHostRole]

    def post(self, request, pk):
        try:
            host = request.user.host_profile
        except HostProfile.DoesNotExist:
            return Response({'error': 'Not a host account.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            booking = (
                Booking.objects
                .select_related('villa__host__user', 'guest')
                .prefetch_related('villa__photos', 'payments')
                .get(pk=pk, villa__host=host)
            )
        except Booking.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        declinable = {Booking.STATUS_PENDING_APPROVAL, Booking.STATUS_PENDING_PAYMENT}
        if booking.status not in declinable:
            return Response(
                {'error': f'Cannot decline a booking with status "{booking.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        booking.status = Booking.STATUS_CANCELLED
        booking.cancelled_at = timezone.now()
        booking.host_responded_at = timezone.now()
        booking.cancellation_reason = request.data.get('reason', 'Declined by host.')
        booking.save()
        return Response({'booking': HostBookingSerializer(booking).data})


def _get_host_booking(request, pk):
    """Returns (booking, error_response). Checks host ownership."""
    try:
        host = request.user.host_profile
    except HostProfile.DoesNotExist:
        return None, Response({'error': 'Not a host account.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        return (
            Booking.objects
            .select_related('villa__host__user', 'guest')
            .prefetch_related('villa__photos', 'payments')
            .get(pk=pk, villa__host=host)
        ), None
    except Booking.DoesNotExist:
        return None, Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)


class HostCheckinView(APIView):
    permission_classes = [HasHostRole]

    def post(self, request, pk):
        booking, err = _get_host_booking(request, pk)
        if err:
            return err
        if booking.status != Booking.STATUS_CONFIRMED:
            return Response(
                {'error': 'Only confirmed bookings can be checked in.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        booking.status = Booking.STATUS_IN_HOUSE
        booking.save(update_fields=['status'])
        return Response({'booking': HostBookingSerializer(booking).data})


class HostCheckoutView(APIView):
    permission_classes = [HasHostRole]

    def post(self, request, pk):
        booking, err = _get_host_booking(request, pk)
        if err:
            return err
        if booking.status != Booking.STATUS_IN_HOUSE:
            return Response(
                {'error': 'Only in-house bookings can be checked out.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        booking.status = Booking.STATUS_COMPLETED
        booking.save(update_fields=['status'])
        return Response({'booking': HostBookingSerializer(booking).data})
