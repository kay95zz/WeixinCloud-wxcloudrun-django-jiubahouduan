from rest_framework import serializers
from .models import Category, Product

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate_price(self, value):
        """验证现金价格是否有效"""
        if value <= 0:
            raise serializers.ValidationError("现金价格必须大于0")
        return value
    
    def validate_points_price(self, value):
        """验证积分价格是否有效"""
        if value < 0:
            raise serializers.ValidationError("积分价格不能为负数")
        return value
    
    def validate(self, data):
        """验证价格关系"""
        # 验证现金价格关系
        original_price = data.get('original_price')
        price = data.get('price')
        
        if original_price and price and original_price <= price:
            raise serializers.ValidationError("现金原价必须大于现价")
        
        # 🆕 验证积分价格关系
        original_points_price = data.get('original_points_price')
        points_price = data.get('points_price')
        
        if original_points_price and points_price and original_points_price <= points_price:
            raise serializers.ValidationError("积分原价必须大于现价")
        
        return data