from django.urls import path
from . import views

urlpatterns = [
    path('', views.VillaListView.as_view()),
    path('featured/', views.VillaFeaturedView.as_view()),
    path('<int:pk>/reviews/', views.VillaReviewsView.as_view()),
    path('<int:pk>/availability/', views.VillaAvailabilityView.as_view()),
    path('<int:pk>/calculate-price/', views.CalculatePriceView.as_view()),
    path('<int:pk>/similar/', views.VillaSimilarView.as_view()),
    path('<slug:slug>/', views.VillaDetailView.as_view()),
]
