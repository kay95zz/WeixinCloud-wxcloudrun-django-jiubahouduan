from rest_framework import serializers
from .models import Shop

class ShopSerializer(serializers.ModelSerializer):
    active_products_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'address', 'phone', 'description', 
            'logo', 'is_active', 'active_products_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'active_products_count']
    
    def validate_name(self, value):
        """验证店铺名称是否唯一"""
        if Shop.objects.filter(name=value).exists():
            raise serializers.ValidationError("店铺名称已存在")
        return value

class ShopCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['name', 'address', 'phone', 'description', 'logo']
    
    def create(self, validated_data):
        shop = Shop.objects.create(**validated_data)
        return shop

class ShopUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['name', 'address', 'phone', 'description', 'logo', 'is_active']