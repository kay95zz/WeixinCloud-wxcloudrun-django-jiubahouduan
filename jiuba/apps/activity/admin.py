# apps/activity/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Activity

class ReservationInline(admin.TabularInline):
    """在活动详情页内联显示预约记录"""
    from apps.reservations.models import Reservation  # 修正导入路径
    model = Reservation
    extra = 0
    readonly_fields = ['user', 'contact_phone', 'status', 'created_at']
    can_delete = False
    max_num = 0  # 禁止在admin中添加新的预约
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'shop', 'start_time', 'end_time', 
        'reservation_stats', 'remaining_slots_display',
        'is_active', 'can_reserve', 'is_featured', 'action_buttons'
    ]
    list_filter = ['shop', 'is_active', 'is_featured', 'start_time']
    list_editable = ['is_featured']
    search_fields = ['title', 'shop__name']
    date_hierarchy = 'start_time'
    readonly_fields = ['created_at', 'updated_at', 'reservation_stats_detailed']
    inlines = [ReservationInline]  # 添加内联显示
    
    # 更合理的字段分组
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'description', 'image', 'shop')
        }),
        ('时间设置', {
            'fields': ('start_time', 'end_time')
        }),
        ('名额设置', {
            'fields': ('max_participants', 'remaining_slots_display')
        }),
        ('状态设置', {
            'fields': ('is_active', 'is_featured')
        }),
        ('预约统计', {
            'fields': ('reservation_stats_detailed',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def reservation_stats(self, obj):
        """在列表页显示预约统计"""
        try:
            from apps.reservations.models import Reservation
            confirmed = Reservation.objects.filter(activity=obj, status='confirmed').count()
            total = Reservation.objects.filter(activity=obj).count()
            
            if total == 0:
                return format_html('<span style="color: #95a5a6;">暂无预约</span>')
            
            return format_html(
                '<span style="color: #2ecc71;">已确认: {}</span> / <span style="color: #3498db;">总计: {}</span>',
                confirmed, total
            )
        except ImportError:
            return format_html('<span style="color: #95a5a6;">预约模块未安装</span>')
    reservation_stats.short_description = '预约统计'

    def remaining_slots_display(self, obj):
        """显示剩余名额"""
        remaining = obj.remaining_slots()
        if remaining == float('inf'):
            return format_html('<span style="color: #2ecc71;">不限名额</span>')
        
        max_participants = obj.max_participants or 0
        percentage = (remaining / max_participants * 100) if max_participants > 0 else 0
        
        if percentage < 20:
            color = '#e74c3c'  # 红色
        elif percentage < 50:
            color = '#f39c12'  # 橙色
        else:
            color = '#2ecc71'  # 绿色
            
        return format_html(
            '<span style="color: {};">{} / {}</span>',
            color, remaining, max_participants
        )
    remaining_slots_display.short_description = '剩余名额'

    def reservation_stats_detailed(self, obj):
        """在详情页显示详细预约统计"""
        try:
            from apps.reservations.models import Reservation
            total = Reservation.objects.filter(activity=obj).count()
            confirmed = Reservation.objects.filter(activity=obj, status='confirmed').count()
            completed = Reservation.objects.filter(activity=obj, status='completed').count()
            cancelled = Reservation.objects.filter(activity=obj, status='cancelled').count()
            
            if total == 0:
                return format_html('<span style="color: #95a5a6;">暂无预约记录</span>')
            
            return format_html('''
                <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                        <div><strong>总预约数:</strong> <span style="color: #3498db;">{}</span></div>
                        <div><strong>已确认:</strong> <span style="color: #2ecc71;">{}</span></div>
                        <div><strong>已完成:</strong> <span style="color: #9b59b6;">{}</span></div>
                        <div><strong>已取消:</strong> <span style="color: #e74c3c;">{}</span></div>
                    </div>
                </div>
            ''', total, confirmed, completed, cancelled)
        except ImportError:
            return format_html('<span style="color: #95a5a6;">预约模块未安装</span>')
    reservation_stats_detailed.short_description = '详细预约统计'

    def action_buttons(self, obj):
        """操作按钮"""
        try:
            from django.contrib import admin
            reservations_url = reverse('admin:reservations_reservation_changelist') + f'?activity__id__exact={obj.id}'
            return format_html(
                '<a class="button" href="{}" style="background: #3498db; color: white; padding: 5px 10px; border-radius: 3px; text-decoration: none; margin-right: 5px;">查看预约</a>'
                '<a class="button" href="{}" style="background: #2ecc71; color: white; padding: 5px 10px; border-radius: 3px; text-decoration: none;">编辑</a>',
                reservations_url,
                f'/admin/activity/activity/{obj.id}/change/'
            )
        except:
            return format_html(
                '<a class="button" href="{}" style="background: #2ecc71; color: white; padding: 5px 10px; border-radius: 3px; text-decoration: none;">编辑</a>',
                f'/admin/activity/activity/{obj.id}/change/'
            )
    action_buttons.short_description = '操作'

    def can_reserve(self, obj):
        return obj.can_reserve()
    can_reserve.boolean = True
    can_reserve.short_description = "可预约"