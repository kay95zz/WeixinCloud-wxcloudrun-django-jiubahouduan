from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from .filters import ProductFilter

class CategoryViewSet(viewsets.ModelViewSet):
    """商品分类视图集"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    pagination_class = None  # 分类通常不需要分页

class ProductViewSet(viewsets.ModelViewSet):
    """商品视图集"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter  # 使用新的过滤器
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'sort_order']
    ordering = ['sort_order', '-created_at']
    
    def get_queryset(self):
        """默认只返回已发布的商品"""
        queryset = super().get_queryset()
        return queryset.filter(status='published', is_available=True)
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """切换商品上架/下架状态"""
        product = self.get_object()
        
        if product.status == 'published':
            product.status = 'draft'
            message = '商品已下架'
        else:
            product.status = 'published'
            message = '商品已上架'
        
        product.save()
        return Response({'status': product.status, 'message': message})
    
    @action(detail=False, methods=['get'])
    def published(self, request):
        """获取已上架的商品列表"""
        queryset = self.get_queryset().filter(status='published', is_available=True)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)