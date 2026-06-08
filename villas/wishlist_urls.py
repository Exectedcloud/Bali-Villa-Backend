from django.urls import path
from . import views

urlpatterns = [
    path('', views.WishlistView.as_view()),
    path('<int:villa_id>/', views.WishlistVillaView.as_view()),
]
