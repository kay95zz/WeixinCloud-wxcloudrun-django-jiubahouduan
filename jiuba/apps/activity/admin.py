from django.contrib import admin
from .models import Activity

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'shop', 'start_time', 'end_time', 'is_active', 'can_reserve', 'is_featured']
    list_filter = ['shop', 'is_active', 'is_featured', 'start_time']  # ← 增加 is_featured 过滤
    list_editable = ['is_featured']  # ← 支持在列表页直接勾选
    search_fields = ['title', 'shop__name']
    date_hierarchy = 'start_time'

    # 在 admin 中显示只读字段
    readonly_fields = ['created_at', 'updated_at']

    def can_reserve(self, obj):
        return obj.can_reserve()
    can_reserve.boolean = True
    can_reserve.short_description = "可预约"