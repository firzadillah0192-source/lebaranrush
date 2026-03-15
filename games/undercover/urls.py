from django.urls import path
from . import views

urlpatterns = [
    path('start/<str:room_code>/', views.api_start_undercover, name='api_start_undercover'),
]
