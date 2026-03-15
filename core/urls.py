from django.urls import path

from . import views

urlpatterns = [
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('helpbot/data/', views.helpbot_data, name='helpbot_data'),
]
