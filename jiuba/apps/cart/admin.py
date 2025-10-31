from django.contrib import admin
from .models import Cart, CartItem

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'shop', 'total_amount', 'total_quantity', 'created_at')
    list_filter = ('shop', 'created_at')
    search_fields = ('user__username', 'shop__name')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'price', 'subtotal')
    list_filter = ('cart__shop',)
    search_fields = ('product__name', 'cart__user__username')
