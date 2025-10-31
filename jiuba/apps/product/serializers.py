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
        """验证价格是否有效"""
        if value <= 0:
            raise serializers.ValidationError("价格必须大于0")
        return value
    
    def validate(self, data):
        """验证原价和现价的关系"""
        original_price = data.get('original_price')
        price = data.get('price')
        
        if original_price and price and original_price <= price:
            raise serializers.ValidationError("原价必须大于现价")
        
        return data