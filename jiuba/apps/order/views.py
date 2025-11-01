# apps/order/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Order, OrderItem
from .serializers import (
    OrderSerializer, CreateOrderSerializer, OrderListSerializer
)
from apps.cart.models import Cart, CartItem
from apps.shop.models import Shop
from django.db.models import Count, Sum, Q

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['order_number', 'customer_notes']
    ordering_fields = ['created_at', 'total_amount', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """获取订单列表"""
        queryset = Order.objects.filter(is_paid=True)  # 只返回已支付订单
        
        # 普通用户只能看到自己的订单
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # 商家只能看到自己店铺的订单
        if hasattr(self.request.user, 'shop'):
            queryset = queryset.filter(shop=self.request.user.shop)
        
        # 根据支付方式过滤
        payment_method = self.request.query_params.get('payment_method')
        if payment_method in ['cash', 'points']:
            queryset = queryset.filter(payment_method=payment_method)
        
        # 根据店铺过滤（管理员用）
        shop_filter = self.request.query_params.get('shop_id')
        if shop_filter and self.request.user.is_staff:
            queryset = queryset.filter(shop_id=shop_filter)
        
        return queryset.select_related('user', 'shop').prefetch_related('items')
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'create':
            return CreateOrderSerializer
        elif self.action == 'list':
            return OrderListSerializer
        return OrderSerializer
    
    @transaction.atomic
    def create(self, request):
        """创建订单（从购物车）- 直接创建为已支付订单"""
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        shop_id = serializer.validated_data['shop_id']
        customer_notes = serializer.validated_data.get('customer_notes', '')
        payment_method = serializer.validated_data['payment_method']
        
        # 获取购物车
        cart = get_object_or_404(
            Cart, 
            user=request.user, 
            shop_id=shop_id
        )
        
        cart_items = cart.items.all()
        if not cart_items:
            return Response(
                {"error": "购物车为空，无法创建订单"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 根据支付方式计算金额
        if payment_method == 'cash':
            total_amount = sum(item.subtotal for item in cart_items)
            total_points = 0
        else:  # points
            total_amount = 0
            total_points = sum(item.points_subtotal for item in cart_items)
        
        # 创建订单（直接设置为已支付）
        from django.utils import timezone
        import random
        import string
        
        order = Order.objects.create(
            user=request.user,
            shop_id=shop_id,
            total_amount=total_amount,
            total_points=total_points,
            payment_method=payment_method,
            customer_notes=customer_notes,
            is_paid=True,
            paid_at=timezone.now(),
            transaction_id=''.join(random.choices(string.ascii_uppercase + string.digits, k=20))
        )
        
        # 创建订单项
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                product_price=cart_item.product.price,
                product_points_price=cart_item.product.points_price,
                quantity=cart_item.quantity
            )
        
        # 清空购物车
        cart.items.all().delete()
        
        return Response(
            OrderSerializer(order).data, 
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取订单统计信息"""
        user = request.user
        
        if user.is_staff:
            # 管理员看到所有订单统计
            queryset = Order.objects.filter(is_paid=True)
        elif hasattr(user, 'shop'):
            # 商家看到自己店铺的订单统计
            queryset = Order.objects.filter(shop=user.shop, is_paid=True)
        else:
            # 普通用户看到自己的订单统计
            queryset = Order.objects.filter(user=user, is_paid=True)
        
        # 应用相同的过滤条件
        payment_method = request.query_params.get('payment_method')
        if payment_method in ['cash', 'points']:
            queryset = queryset.filter(payment_method=payment_method)
        
        shop_filter = request.query_params.get('shop_id')
        if shop_filter and user.is_staff:
            queryset = queryset.filter(shop_id=shop_filter)
        
        # 计算统计信息
        stats = queryset.aggregate(
            total_orders=Count('id'),
            total_cash_amount=Sum('total_amount'),
            total_points_amount=Sum('total_points'),
            cash_orders=Count('id', filter=Q(payment_method='cash')),  # 使用 Q 而不是 models.Q
            points_orders=Count('id', filter=Q(payment_method='points'))  # 使用 Q 而不是 models.Q
        )
        
        return Response({
            "total_orders": stats['total_orders'] or 0,
            "total_cash_amount": float(stats['total_cash_amount'] or 0),
            "total_points_amount": stats['total_points_amount'] or 0,
            "cash_orders": stats['cash_orders'] or 0,
            "points_orders": stats['points_orders'] or 0
        })
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """导出订单数据"""
        from django.http import HttpResponse
        import csv
        from django.utils import timezone
        
        queryset = self.get_queryset()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="orders_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            '订单号', '用户', '店铺', '支付方式', '现金金额', '积分金额', 
            '商品数量', '顾客备注', '创建时间', '支付时间', '交易号'
        ])
        
        for order in queryset:
            writer.writerow([
                order.order_number,
                order.user.username,
                order.shop.name,
                order.get_payment_method_display(),
                float(order.total_amount),
                order.total_points,
                order.item_count,
                order.customer_notes,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.paid_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.transaction_id
            ])
        
        return response