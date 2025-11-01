from rest_framework import serializers
from .models import Notice

class NoticeSerializer(serializers.ModelSerializer):
    """公告序列化器 - 简化版"""
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    
    class Meta:
        model = Notice
        fields = ['id', 'shop', 'shop_name', 'title', 'content', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']