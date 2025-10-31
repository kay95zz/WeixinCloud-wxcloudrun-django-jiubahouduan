from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone', 'balance', 'points', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'phone')
    ordering = ('-date_joined',)
    fieldsets = UserAdmin.fieldsets + (
        ('额外信息', {'fields': ('phone', 'balance', 'points', 'avatar', 'shop')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('额外信息', {
            'classes': ('wide',),
            'fields': ('phone', 'balance', 'points', 'avatar', 'shop'),
        }),
    )