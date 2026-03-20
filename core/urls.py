from django.urls import path

from . import views

urlpatterns = [
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('helpbot/data/', views.helpbot_data, name='helpbot_data'),
    path('help/ticket/create/', views.create_ticket, name='create_ticket'),
    path('help/ticket/my/', views.my_tickets, name='my_tickets'),
    path('help/ticket/<int:ticket_id>/messages/', views.ticket_messages, name='ticket_messages'),
    path('help/ticket/<int:ticket_id>/reply/', views.reply_ticket, name='reply_ticket'),
]
