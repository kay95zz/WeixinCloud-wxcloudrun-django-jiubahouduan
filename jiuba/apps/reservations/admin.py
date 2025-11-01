# apps/reservation/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Reservation

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'activity_title', 'shop_name', 
        'contact_phone', 'status_display', 'created_at', 'action_buttons'
    ]
    list_filter = ['status', 'activity__shop', 'created_at']
    search_fields = ['user__username', 'activity__title', 'contact_phone']
    readonly_fields = ['created_at', 'reservation_info']
    list_per_page = 20
    
    fieldsets = (
        ('预约信息', {
            'fields': ('reservation_info',)
        }),
        ('用户信息', {
            'fields': ('user', 'contact_phone', 'note')
        }),
        ('活动信息', {
            'fields': ('activity', 'shop')
        }),
        ('状态管理', {
            'fields': ('status',)
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def activity_title(self, obj):
        return obj.activity.title
    activity_title.short_description = '活动名称'

    def shop_name(self, obj):
        return obj.shop.name
    shop_name.short_description = '店铺'

    def status_display(self, obj):
        status_colors = {
            'confirmed': 'success',
            'completed': 'info', 
            'cancelled': 'danger'
        }
        color = status_colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = '状态'

    def reservation_info(self, obj):
        """显示预约详细信息"""
        return format_html('''
            <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
                <h4>预约详情</h4>
                <p><strong>预约ID:</strong> {}</p>
                <p><strong>用户:</strong> {}</p>
                <p><strong>活动:</strong> {}</p>
                <p><strong>店铺:</strong> {}</p>
                <p><strong>联系电话:</strong> {}</p>
                <p><strong>状态:</strong> {}</p>
                <p><strong>创建时间:</strong> {}</p>
            </div>
        ''', obj.id, obj.user.username, obj.activity.title, 
           obj.shop.name, obj.contact_phone, 
           obj.get_status_display(), obj.created_at.strftime('%Y-%m-%d %H:%M:%S'))
    reservation_info.short_description = '预约详情'

    def action_buttons(self, obj):
        """操作按钮"""
        return format_html(
            '<a class="button" href="{}">查看详情</a>',
            f'/admin/reservation/reservation/{obj.id}/change/'
        )
    action_buttons.short_description = '操作'

    # 自定义actions
    actions = ['mark_as_confirmed', 'mark_as_completed', 'mark_as_cancelled']
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated}个预约已标记为已确认')
    mark_as_confirmed.short_description = "标记为已确认"
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated}个预约已标记为已完成')
    mark_as_completed.short_description = "标记为已完成"
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated}个预约已标记为已取消')
    mark_as_cancelled.short_description = "标记为已取消"