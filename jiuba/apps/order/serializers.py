from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusLog
from apps.product.serializers import ProductSerializer
from apps.shop.serializers import ShopSerializer
from apps.user.serializers import UserSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_detail', 'product_name', 
            'product_price', 'quantity', 'subtotal'
        ]
        read_only_fields = ['product_name', 'product_price']
    
    def get_subtotal(self, obj):
        return obj.subtotal

class OrderStatusLogSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = OrderStatusLog
        fields = ['id', 'from_status', 'to_status', 'notes', 'created_at', 'created_by_name']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_logs = OrderStatusLogSerializer(many=True, read_only=True)
    user_detail = UserSerializer(source='user', read_only=True)
    shop_detail = ShopSerializer(source='shop', read_only=True)
    item_count = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'user_detail', 'shop', 'shop_detail',
            'total_amount', 'discount_amount', 'actual_amount', 'status',
            'status_display', 'payment_method', 'is_paid', 'paid_at',
            'transaction_id', 'items', 'status_logs', 'item_count',
            'customer_notes', 'admin_notes', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'order_number', 'total_amount', 'actual_amount', 'is_paid',
            'paid_at', 'transaction_id', 'created_at', 'updated_at', 'completed_at'
        ]

class CreateOrderSerializer(serializers.Serializer):
    """创建订单序列化器"""
    shop_id = serializers.IntegerField()
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_METHOD_CHOICES)
    
    def validate_shop_id(self, value):
        """验证店铺是否存在"""
        from apps.shop.models import Shop
        try:
            shop = Shop.objects.get(id=value, is_active=True)
        except Shop.DoesNotExist:
            raise serializers.ValidationError("店铺不存在或已停用")
        return value

class UpdateOrderStatusSerializer(serializers.Serializer):
    """更新订单状态序列化器"""
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)

class OrderListSerializer(serializers.ModelSerializer):
    """订单列表序列化器（简化版）"""
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    item_count = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'shop_name', 'total_amount', 'actual_amount',
            'status', 'status_display', 'is_paid', 'item_count', 'created_at'
        ]