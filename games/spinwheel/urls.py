from django.urls import path
from . import views

urlpatterns = [
    path('guest-spin/<uuid:token>/', views.guest_spin_page, name='guest_spin_page'),
    path('guest-spin/<uuid:token>/process/', views.process_guest_spin, name='process_guest_spin'),
]
