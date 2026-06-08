from django.urls import path
from . import views

urlpatterns = [
    path('', views.ConversationListView.as_view()),
    path('<int:pk>/messages/', views.MessageListView.as_view()),
]
