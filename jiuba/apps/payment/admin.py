from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['out_trade_no', 'order', 'user', 'amount', 'method', 'status', 'paid_at']
    list_filter = ['method', 'status', 'created_at']
    search_fields = ['out_trade_no', 'transaction_id', 'user__username']
    readonly_fields = ['created_at', 'paid_at', 'refunded_at']