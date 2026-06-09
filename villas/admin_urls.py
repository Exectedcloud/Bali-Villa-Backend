from django.urls import path
from .admin_views import AdminPendingVillaListView, AdminVillaActionView

urlpatterns = [
    path('pending/', AdminPendingVillaListView.as_view(), name='admin-pending-villas'),
    path('<int:pk>/<str:action>/', AdminVillaActionView.as_view(), name='admin-villa-action'),
]
