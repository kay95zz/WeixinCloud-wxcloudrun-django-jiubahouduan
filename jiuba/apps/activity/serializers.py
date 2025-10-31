from rest_framework import serializers
from .models import Activity

class ActivitySerializer(serializers.ModelSerializer):
    """基础活动序列化器"""
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    shop_address = serializers.CharField(source='shop.address', read_only=True)
    
    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'description', 'start_time', 'end_time',
            'price', 'original_price', 'max_participants', 'current_participants',
            'cover_image', 'is_featured', 'is_active', 'shop_id',
            'shop_name', 'shop_address', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class ActivityDetailSerializer(serializers.ModelSerializer):
    """详细活动序列化器 - 包含更多信息"""
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    shop_address = serializers.CharField(source='shop.address', read_only=True)
    shop_phone = serializers.CharField(source='shop.phone', read_only=True)
    shop_description = serializers.CharField(source='shop.description', read_only=True)
    
    # 添加活动状态字段
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'description', 'detailed_description',
            'start_time', 'end_time', 'price', 'original_price',
            'max_participants', 'current_participants', 'cover_image',
            'images', 'is_featured', 'is_active', 'shop_id',
            'shop_name', 'shop_address', 'shop_phone', 'shop_description',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_status(self, obj):
        """计算活动状态"""
        from django.utils import timezone
        now = timezone.now()
        
        if obj.end_time < now:
            return 'ended'
        elif obj.start_time <= now <= obj.end_time:
            return 'ongoing'
        elif now < obj.start_time:
            return 'upcoming'
        else:
            return 'unknown'