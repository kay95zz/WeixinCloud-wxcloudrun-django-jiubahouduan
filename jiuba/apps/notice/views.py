from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from .models import Notice
from .serializers import NoticeSerializer

class NoticeViewSet(viewsets.ModelViewSet):
    """
    公告管理 ViewSet - 简化版
    """
    queryset = Notice.objects.all().select_related('shop')
    serializer_class = NoticeSerializer
    
    def get_permissions(self):
        """
        简化权限控制：
        - 查看：所有用户可访问
        - 增删改：需要登录
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_queryset(self):
        """获取公告列表，默认只显示启用的公告"""
        queryset = super().get_queryset()
        
        # 普通用户只能看到启用的公告
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def shop_notices(self, request):
        """获取指定店铺的公告列表"""
        shop_id = request.query_params.get('shop_id')
        if not shop_id:
            return Response(
                {"error": "请提供shop_id参数"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(shop_id=shop_id)
        
        # 序列化并返回
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """切换公告启用状态"""
        notice = self.get_object()
        notice.is_active = not notice.is_active
        notice.save()
        
        message = f"公告{'已启用' if notice.is_active else '已停用'}"
        return Response({
            "message": message,
            "is_active": notice.is_active
        })