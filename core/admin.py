from django.contrib import admin

from .models import ChatbotSetting, HelpContact, HelpOption, SiteVisit


@admin.register(SiteVisit)
class SiteVisitAdmin(admin.ModelAdmin):
    list_display = ('path', 'session_key', 'ip_address', 'visited_at')
    list_filter = ('path', 'visited_at')
    search_fields = ('session_key', 'ip_address', 'user_agent')
    readonly_fields = ('path', 'session_key', 'ip_address', 'user_agent', 'visited_at')


@admin.register(HelpContact)
class HelpContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_type', 'contact_value', 'is_active')
    list_filter = ('contact_type', 'is_active')
    search_fields = ('name', 'contact_value')


@admin.register(HelpOption)
class HelpOptionAdmin(admin.ModelAdmin):
    list_display = ('title', 'sort_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'answer')
    ordering = ('sort_order', 'title')


@admin.register(ChatbotSetting)
class ChatbotSettingAdmin(admin.ModelAdmin):
    list_display = ('bubble_label', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('bubble_label', 'greeting')
