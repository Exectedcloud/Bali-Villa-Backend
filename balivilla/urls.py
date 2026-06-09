from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from villas.views import RegionStatsView


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'ok', 'service': 'balivilla-api', 'version': 'v1'})


urlpatterns = [
    path('admin/', admin.site.urls),

    # Health check — public
    path('api/v1/', health_check),

    # App routers
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/profile/', include('users.profile_urls')),
    path('api/v1/villas/', include('villas.urls')),
    path('api/v1/wishlist/', include('villas.wishlist_urls')),
    path('api/v1/bookings/', include('bookings.urls')),
    # path('api/v1/payments/', include('payments.urls')),
    path('api/v1/conversations/', include('messaging.urls')),
    path('api/v1/messages/', include('messaging.message_urls')),
    path('api/v1/host/', include('balivilla.host_urls')),
    path('api/v1/admin/villas/', include('villas.admin_urls')),

    # Regions — not nested under /villas/ per spec
    path('api/v1/regions/stats/', RegionStatsView.as_view()),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
