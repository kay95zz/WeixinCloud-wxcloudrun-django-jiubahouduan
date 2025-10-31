from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from .models import Shop
from .serializers import ShopSerializer, ShopCreateSerializer, ShopUpdateSerializer

class ShopViewSet(viewsets.ModelViewSet):
    queryset = Shop.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'address', 'phone']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """
        根据动作设置权限
        - 列表和详情：所有用户可访问
        - 创建、更新、删除：需要管理员权限
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'toggle_status']:
            permission_classes = [IsAuthenticated, IsAdminUser]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """根据动作选择不同的序列化器"""
        if self.action == 'create':
            return ShopCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ShopUpdateSerializer
        return ShopSerializer
    
    def get_queryset(self):
        """获取店铺列表，管理员可以看到所有店铺，普通用户只能看到活跃店铺"""
        queryset = super().get_queryset()
        
        # 如果是管理员，返回所有店铺
        if self.request.user.is_staff:
            return queryset
        
        # 普通用户只能看到活跃店铺
        return queryset.filter(is_active=True)
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """切换店铺激活状态（管理员功能）"""
        if not request.user.is_staff:
            return Response(
                {"error": "只有管理员可以执行此操作"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        shop = self.get_object()
        shop.is_active = not shop.is_active
        shop.save()
        
        message = f"店铺{'已激活' if shop.is_active else '已停用'}"
        return Response({
            "message": message,
            "is_active": shop.is_active
        })
    
    @action(detail=False, methods=['get'])
    def active_shops(self, request):
        """获取所有活跃店铺列表"""
        queryset = self.get_queryset().filter(is_active=True)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """获取指定店铺的商品列表"""
        shop = self.get_object()
        products = shop.products.filter(is_available=True, status='published')
        
        # 这里可以添加商品分页逻辑
        from apps.product.serializers import ProductSerializer
        serializer = ProductSerializer(products, many=True)
        
        return Response({
            'shop': shop.name,
            'products': serializer.data
        })