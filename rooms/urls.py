from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('host/', views.create_room, name='create_room'),
    path('host/create/', views.create_room, name='create_room_legacy'),
    path('host/<str:room_code>/', views.host_dashboard, name='host_dashboard'),
    path('join/', views.join_index, name='join_index'),
    path('join/<str:room_code>/', views.join_room, name='join_room'),
    path('play/<str:room_code>/', views.player_lobby, name='player_lobby'),
]
