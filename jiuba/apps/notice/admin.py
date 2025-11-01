from django.contrib import admin
from .models import Notice

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ['title', 'shop', 'is_active', 'created_at']
    list_filter = ['shop', 'is_active', 'created_at']
    search_fields = ['title', 'content', 'shop__name']
    list_editable = ['is_active']
    
    fieldsets = (
        (None, {
            'fields': ('shop', 'title', 'content', 'is_active')
        }),
    )