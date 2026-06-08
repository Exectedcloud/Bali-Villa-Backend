from django.urls import path
from .views import MessageReadView

urlpatterns = [
    path('<int:pk>/read/', MessageReadView.as_view()),
]
