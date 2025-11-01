# apps/orders/serializers.py
# apps/order/serializers.py
from rest_framework import serializers
from .models import Order, OrderItem
from apps.product.serializers import ProductSerializer
from apps.shop.serializers import ShopSerializer
from apps.user.serializers import UserSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)
    subtotal = serializers.SerializerMethodField()
    points_subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_detail', 'product_name', 
            'product_price', 'product_points_price', 'quantity', 
            'subtotal', 'points_subtotal'
        ]
        read_only_fields = ['product_name', 'product_price', 'product_points_price']
    
    def get_subtotal(self, obj):
        return obj.subtotal
    
    def get_points_subtotal(self, obj):
        return obj.points_subtotal

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_detail = UserSerializer(source='user', read_only=True)
    shop_detail = ShopSerializer(source='shop', read_only=True)
    item_count = serializers.ReadOnlyField()
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    calculated_total = serializers.SerializerMethodField()
    calculated_total_points = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'user_detail', 'shop', 'shop_detail',
            'total_amount', 'total_points', 'payment_method', 'payment_method_display',
            'is_paid', 'paid_at', 'transaction_id', 'items', 'item_count',
            'customer_notes', 'created_at', 'updated_at',
            'calculated_total', 'calculated_total_points'
        ]
        read_only_fields = [
            'order_number', 'total_amount', 'total_points', 'is_paid',
            'paid_at', 'transaction_id', 'created_at', 'updated_at'
        ]
    
    def get_calculated_total(self, obj):
        return obj.calculated_total_amount
    
    def get_calculated_total_points(self, obj):
        return obj.calculated_total_points

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

class OrderListSerializer(serializers.ModelSerializer):
    """订单列表序列化器（简化版）"""
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    item_count = serializers.ReadOnlyField()
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'shop_name', 'user_name', 
            'total_amount', 'total_points', 'payment_method', 'payment_method_display',
            'is_paid', 'item_count', 'created_at', 'paid_at'
        ]