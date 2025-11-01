from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('is_active',)
    list_per_page = 20
    
    def product_count(self, obj):
        """显示该分类下的商品数量"""
        return obj.product_set.count()
    product_count.short_description = '商品数量'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'shop', 'category', 'price', 'original_price', 
        'points_price', 'original_points_price',
        'status', 'is_available', 'stock_quantity', 'stock_status', 
        'created_at', 'display_image'
    )
    list_filter = ('status', 'is_available', 'category', 'shop', 'created_at')
    search_fields = ('name', 'description', 'shop__name', 'category__name')
    list_editable = ('price', 'points_price', 'status', 'is_available', 'stock_quantity')
    readonly_fields = ('created_at', 'updated_at', 'stock_status', 'points_status')
    list_per_page = 20
    
    # 更合理的字段分组
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'shop', 'category')
        }),
        ('现金价格', {
            'fields': ('price', 'original_price'),
        }),
        ('积分价格', {
            'fields': ('points_price', 'original_points_price', 'points_status'),
            'classes': ('collapse',)
        }),
        ('库存与状态', {
            'fields': ('stock_quantity', 'stock_status', 'status', 'is_available')
        }),
        ('媒体与排序', {
            'fields': ('image', 'sort_order'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_image(self, obj):
        """显示图片预览"""
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "无图片"
    display_image.short_description = '图片预览'
    
    def stock_status(self, obj):
        """库存状态显示（只读）"""
        if obj.stock_quantity <= 0:
            return format_html('<span style="color: red; font-weight: bold;">缺货</span>')
        elif obj.stock_quantity < 10:
            return format_html('<span style="color: orange; font-weight: bold;">低库存({})</span>', obj.stock_quantity)
        else:
            return format_html('<span style="color: green;">充足({})</span>', obj.stock_quantity)
    stock_status.short_description = '库存状态'
    
    def points_price_display(self, obj):
        """积分价格显示"""
        if obj.points_price > 0:
            if obj.is_points_on_sale:
                return format_html(
                    '<span style="color: #e74c3c; font-weight: bold;">{}积分</span><br><small style="color: #95a5a6; text-decoration: line-through;">{}积分</small>',
                    obj.points_price, obj.original_points_price
                )
            else:
                return format_html(
                    '<span style="color: #2ecc71; font-weight: bold;">{}积分</span>',
                    obj.points_price
                )
        else:
            return format_html('<span style="color: #95a5a6;">不支持积分</span>')
    points_price_display.short_description = '积分价格'
    
    def points_original_price_display(self, obj):
        """积分原价显示"""
        if obj.original_points_price and obj.original_points_price > 0:
            return f"{obj.original_points_price}积分"
        return "-"
    points_original_price_display.short_description = '积分原价'
    
    def points_status(self, obj):
        """积分购买状态显示（只读）"""
        if obj.points_price > 0:
            if obj.is_points_on_sale:
                return format_html('<span style="color: #e74c3c; font-weight: bold;">积分折扣中</span>')
            else:
                return format_html('<span style="color: #2ecc71;">支持积分购买</span>')
        else:
            return format_html('<span style="color: #95a5a6;">不支持积分</span>')
    points_status.short_description = '积分状态'

    # 自定义actions
    actions = ['make_published', 'make_draft', 'toggle_availability', 'enable_points', 'disable_points']
    
    def make_published(self, request, queryset):
        """批量上架商品"""
        updated = queryset.update(status='published')
        self.message_user(request, f'{updated}个商品已上架')
    make_published.short_description = "上架选中的商品"
    
    def make_draft(self, request, queryset):
        """批量下架商品"""
        updated = queryset.update(status='draft')
        self.message_user(request, f'{updated}个商品已下架')
    make_draft.short_description = "下架选中的商品"
    
    def toggle_availability(self, request, queryset):
        """切换可用状态"""
        for obj in queryset:
            obj.is_available = not obj.is_available
            obj.save()
        self.message_user(request, f'{queryset.count()}个商品状态已切换')
    toggle_availability.short_description = "切换可用状态"
    
    def enable_points(self, request, queryset):
        """启用积分购买"""
        for obj in queryset:
            if obj.points_price == 0:
                obj.points_price = int(obj.price * 10)  # 默认设置积分价格为现金价格的10倍
            obj.save()
        self.message_user(request, f'{queryset.count()}个商品已启用积分购买')
    enable_points.short_description = "启用积分购买"
    
    def disable_points(self, request, queryset):
        """禁用积分购买"""
        updated = queryset.update(points_price=0, original_points_price=0)
        self.message_user(request, f'{updated}个商品已禁用积分购买')
    disable_points.short_description = "禁用积分购买"