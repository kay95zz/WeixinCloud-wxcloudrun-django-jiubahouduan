from django.contrib import admin
from django.utils.html import format_html
from .models import Shop

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'address', 'phone', 'is_active', 
        'active_products_count', 'created_at', 'display_logo'
    )
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'address', 'phone')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at', 'active_products_count')
    fieldsets = (
        (None, {
            'fields': ('name', 'address', 'phone', 'description')
        }),
        ('图片', {
            'fields': ('logo',)
        }),
        ('状态', {
            'fields': ('is_active',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_logo(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="50" height="50" />', obj.logo.url)
        return "无Logo"
    display_logo.short_description = 'Logo预览'
    
    def active_products_count(self, obj):
        return obj.products.filter(is_available=True, status='published').count()
    active_products_count.short_description = '活跃商品数'