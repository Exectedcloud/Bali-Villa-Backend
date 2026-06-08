from django.urls import path
from . import views

urlpatterns = [
    path('', views.BookingListView.as_view()),
    path('draft/', views.DraftBookingView.as_view()),
    path('<int:pk>/', views.BookingDetailView.as_view()),
    path('<int:pk>/cancel/', views.BookingCancelView.as_view()),
    path('<int:pk>/confirm/', views.BookingConfirmView.as_view()),
    path('<int:pk>/review/', views.BookingReviewView.as_view()),
    path('<int:pk>/promo/', views.BookingPromoView.as_view()),
    path('<int:pk>/modify/', views.BookingModifyView.as_view()),
]
