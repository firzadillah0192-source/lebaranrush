from django.contrib import admin
from django.utils.html import format_html
from .models import GuestSpinToken

@admin.register(GuestSpinToken)
class GuestSpinTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'room', 'guest_name', 'is_used', 'created_at', 'qr_link')
    list_filter = ('is_used', 'room')
    search_fields = ('guest_name', 'token')
    
    def qr_link(self, obj):
        url = f"/guest-spin/{obj.token}/"
        return format_html('<a href="{}" target="_blank">View Guest Page</a>', url)
    
    qr_link.short_description = 'Guest Page'
