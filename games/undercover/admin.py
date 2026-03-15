from django.contrib import admin
from .models import UndercoverWord

@admin.register(UndercoverWord)
class UndercoverWordAdmin(admin.ModelAdmin):
    list_display = ('word_common', 'word_undercover', 'category', 'is_active', 'created_at')
    list_filter = ('is_active', 'category')
    search_fields = ('word_common', 'word_undercover', 'category')
    ordering = ('-created_at',)
