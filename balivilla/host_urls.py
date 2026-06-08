from django.urls import path
from users.host_views import HostSignupView, HostLoginView, HostMeView
from villas.host_views import (
    HostVillaListView, HostVillaDetailView,
    HostCalendarView, HostCalendarBlockView, HostCalendarPriceView,
)
from bookings.host_views import (
    HostBookingListView, HostBookingDetailView,
    HostBookingApproveView, HostBookingDeclineView,
    HostCheckinView, HostCheckoutView,
)
from messaging.host_views import HostConversationListView, HostMessageListView

urlpatterns = [
    # Auth
    path('signup/', HostSignupView.as_view(), name='host-signup'),
    path('login/', HostLoginView.as_view(), name='host-login'),
    path('me/', HostMeView.as_view(), name='host-me'),
    # Listings (spec: /host/listings/)
    path('listings/', HostVillaListView.as_view(), name='host-listing-list'),
    path('listings/<int:pk>/', HostVillaDetailView.as_view(), name='host-listing-detail'),
    # Reservations (spec: /host/reservations/)
    path('reservations/', HostBookingListView.as_view(), name='host-reservation-list'),
    path('reservations/<int:pk>/', HostBookingDetailView.as_view(), name='host-reservation-detail'),
    path('reservations/<int:pk>/approve/', HostBookingApproveView.as_view(), name='host-reservation-approve'),
    path('reservations/<int:pk>/decline/', HostBookingDeclineView.as_view(), name='host-reservation-decline'),
    path('reservations/<int:pk>/check-in/', HostCheckinView.as_view(), name='host-reservation-checkin'),
    path('reservations/<int:pk>/check-out/', HostCheckoutView.as_view(), name='host-reservation-checkout'),
    # Calendar
    path('calendar/', HostCalendarView.as_view(), name='host-calendar'),
    path('calendar/block/', HostCalendarBlockView.as_view(), name='host-calendar-block'),
    path('calendar/price/', HostCalendarPriceView.as_view(), name='host-calendar-price'),
    # Conversations
    path('conversations/', HostConversationListView.as_view(), name='host-conversation-list'),
    path('conversations/<int:pk>/messages/', HostMessageListView.as_view(), name='host-message-list'),
]
