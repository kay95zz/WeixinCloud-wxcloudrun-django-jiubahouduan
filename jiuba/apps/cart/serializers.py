from rest_framework import serializers
from .models import Cart, CartItem
from apps.product.serializers import ProductSerializer

class CartItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_detail', 'quantity', 'price', 'subtotal', 'created_at']
        read_only_fields = ['price', 'created_at']
    
    def get_subtotal(self, obj):
        return obj.subtotal
    
    def validate_quantity(self, value):
        """验证数量是否有效"""
        if value <= 0:
            raise serializers.ValidationError("数量必须大于0")
        return value

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'shop', 'items', 'total_amount', 'total_quantity', 'created_at', 'updated_at']
        read_only_fields = ['user', 'total_amount', 'total_quantity']
    
    def get_total_amount(self, obj):
        return obj.total_amount
    
    def get_total_quantity(self, obj):
        return obj.total_quantity

class AddToCartSerializer(serializers.Serializer):
    """添加到购物车序列化器"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    
    def validate_product_id(self, value):
        """验证商品是否存在且可用"""
        from apps.product.models import Product
        try:
            product = Product.objects.get(id=value, is_available=True, status='published')
        except Product.DoesNotExist:
            raise serializers.ValidationError("商品不存在或不可用")
        return value

class UpdateCartItemSerializer(serializers.Serializer):
    """更新购物车项序列化器"""
    quantity = serializers.IntegerField(min_value=1)
