from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, OrderStatusLog

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'product_price', 'subtotal']
    
    def subtotal(self, obj):
        return obj.subtotal
    subtotal.short_description = '小计'

class OrderStatusLogInline(admin.TabularInline):
    model = OrderStatusLog
    extra = 0
    readonly_fields = ['from_status', 'to_status', 'notes', 'created_at', 'created_by']
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'user', 'shop', 'total_amount', 'actual_amount',
        'status', 'is_paid', 'item_count', 'created_at', 'action_buttons'  # 将actions改为action_buttons
    ]
    list_filter = ['status', 'is_paid', 'shop', 'created_at']
    search_fields = ['order_number', 'user__username', 'shop__name']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'paid_at', 'completed_at']
    inlines = [OrderItemInline, OrderStatusLogInline]
    actions = ['mark_as_paid', 'mark_as_completed', 'mark_as_cancelled']  # 这是批量操作

    def action_buttons(self, obj):  # 重命名方法
        return format_html(
            '<a class="button" href="{}">查看详情</a>',
            f'/admin/ordering/order/{obj.id}/change/'
        )
    action_buttons.short_description = '操作'
    
    def mark_as_paid(self, request, queryset):
        queryset.update(is_paid=True, status='paid')
    mark_as_paid.short_description = "标记为已支付"
    
    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='completed', completed_at=timezone.now())
    mark_as_completed.short_description = "标记为已完成"
    
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
    mark_as_cancelled.short_description = "标记为已取消"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'product_name', 'product_price', 'quantity', 'subtotal']
    list_filter = ['order__shop']
    search_fields = ['order__order_number', 'product__name']
    
    def subtotal(self, obj):
        return obj.subtotal
    subtotal.short_description = '小计'

@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ['order', 'from_status', 'to_status', 'created_at', 'created_by']
    list_filter = ['to_status', 'created_at']
    search_fields = ['order__order_number']
    readonly_fields = ['order', 'from_status', 'to_status', 'notes', 'created_at', 'created_by']