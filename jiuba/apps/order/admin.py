# apps/order/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'product_price', 'product_points_price', 'subtotal', 'points_subtotal']
    
    def subtotal(self, obj):
        return f"¥{obj.subtotal}"
    subtotal.short_description = '现金小计'
    
    def points_subtotal(self, obj):
        return f"{obj.points_subtotal} 积分"
    points_subtotal.short_description = '积分小计'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'user', 'shop', 'payment_method_display', 
        'total_amount_display', 'total_points_display', 'item_count', 
        'created_at', 'paid_at', 'action_buttons'
    ]
    list_filter = ['payment_method', 'shop', 'created_at']
    search_fields = ['order_number', 'user__username', 'shop__name']
    readonly_fields = [
        'order_number', 'created_at', 'updated_at', 'paid_at', 
        'transaction_id', 'calculated_total', 'calculated_total_points'
    ]
    inlines = [OrderItemInline]
    actions = ['export_selected_orders']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('order_number', 'user', 'shop', 'payment_method')
        }),
        ('金额信息', {
            'fields': ('total_amount', 'total_points', 'calculated_total', 'calculated_total_points')
        }),
        ('支付信息', {
            'fields': ('is_paid', 'paid_at', 'transaction_id')
        }),
        ('备注信息', {
            'fields': ('customer_notes',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def payment_method_display(self, obj):
        """支付方式显示"""
        if obj.payment_method == 'cash':
            return format_html('<span class="badge bg-success">{}</span>', '现金支付')
        else:
            return format_html('<span class="badge bg-warning">{}</span>', '积分支付')
    payment_method_display.short_description = '支付方式'
    
    def total_amount_display(self, obj):
        """现金金额显示"""
        return f"¥{obj.total_amount}"
    total_amount_display.short_description = '现金金额'
    
    def total_points_display(self, obj):
        """积分金额显示"""
        return f"{obj.total_points} 积分"
    total_points_display.short_description = '积分金额'
    
    def calculated_total(self, obj):
        """计算现金总金额"""
        return f"¥{obj.calculated_total_amount}"
    calculated_total.short_description = '计算现金总金额'
    
    def calculated_total_points(self, obj):
        """计算积分总金额"""
        return f"{obj.calculated_total_points} 积分"
    calculated_total_points.short_description = '计算积分总金额'
    
    def action_buttons(self, obj):
        """操作按钮"""
        return format_html(
            '<a class="button" href="{}">查看详情</a>',
            f'/admin/order/order/{obj.id}/change/'
        )
    action_buttons.short_description = '操作'
    
    def export_selected_orders(self, request, queryset):
        """导出选中订单"""
        import csv
        from django.http import HttpResponse
        from django.utils import timezone
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="orders_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            '订单号', '用户', '店铺', '支付方式', '现金金额', '积分金额', 
            '商品数量', '顾客备注', '创建时间', '支付时间', '交易号'
        ])
        
        for order in queryset:
            writer.writerow([
                order.order_number,
                order.user.username,
                order.shop.name,
                order.get_payment_method_display(),
                float(order.total_amount),
                order.total_points,
                order.item_count,
                order.customer_notes,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.paid_at.strftime('%Y-%m-%d %H:%M:%S') if order.paid_at else '',
                order.transaction_id
            ])
        
        self.message_user(request, f'成功导出 {queryset.count()} 个订单')
        return response
    export_selected_orders.short_description = "导出选中订单"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'order', 'product', 'product_name', 'quantity', 
        'product_price_display', 'product_points_price_display',
        'subtotal_display', 'points_subtotal_display'
    ]
    list_filter = ['order__shop', 'order__payment_method']
    search_fields = ['order__order_number', 'product__name', 'product_name']
    readonly_fields = ['product_name', 'product_price', 'product_points_price']
    
    def product_price_display(self, obj):
        return f"¥{obj.product_price}"
    product_price_display.short_description = '商品单价'
    
    def product_points_price_display(self, obj):
        return f"{obj.product_points_price} 积分"
    product_points_price_display.short_description = '商品积分价'
    
    def subtotal_display(self, obj):
        return f"¥{obj.subtotal}"
    subtotal_display.short_description = '现金小计'
    
    def points_subtotal_display(self, obj):
        return f"{obj.points_subtotal} 积分"
    points_subtotal_display.short_description = '积分小计'