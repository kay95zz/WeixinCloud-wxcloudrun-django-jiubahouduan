from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Order, OrderItem, OrderStatusLog
from .serializers import (
    OrderSerializer, CreateOrderSerializer, UpdateOrderStatusSerializer,
    OrderListSerializer, OrderStatusLogSerializer
)
from apps.cart.models import Cart, CartItem
from apps.shop.models import Shop

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['order_number', 'customer_notes']
    ordering_fields = ['created_at', 'total_amount', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """获取订单列表"""
        queryset = Order.objects.all()
        
        # 普通用户只能看到自己的订单
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # 根据状态过滤
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 根据店铺过滤
        shop_filter = self.request.query_params.get('shop_id')
        if shop_filter:
            queryset = queryset.filter(shop_id=shop_filter)
        
        return queryset
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'create':
            return CreateOrderSerializer
        elif self.action == 'list':
            return OrderListSerializer
        elif self.action == 'update_status':
            return UpdateOrderStatusSerializer
        return OrderSerializer
    
    @transaction.atomic
    def create(self, request):
        """创建订单（从购物车）"""
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
        
        # 计算总金额
        total_amount = sum(item.subtotal for item in cart_items)
        
        # 创建订单
        order = Order.objects.create(
            user=request.user,
            shop_id=shop_id,
            total_amount=total_amount,
            discount_amount=0,  # 可以在这里添加优惠逻辑
            customer_notes=customer_notes,
            payment_method=payment_method
        )
        
        # 创建订单项
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                product_price=cart_item.product.price,
                quantity=cart_item.quantity
            )
        
        # 记录状态变更
        OrderStatusLog.objects.create(
            order=order,
            from_status='',
            to_status='pending',
            notes='订单创建',
            created_by=request.user
        )
        
        # 清空购物车
        cart.items.all().delete()
        
        return Response(
            OrderSerializer(order).data, 
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """更新订单状态"""
        order = self.get_object()
        serializer = UpdateOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')
        
        # 记录状态变更
        OrderStatusLog.objects.create(
            order=order,
            from_status=order.status,
            to_status=new_status,
            notes=notes,
            created_by=request.user
        )
        
        # 更新订单状态
        order.status = new_status
        
        # 如果是完成状态，记录完成时间
        if new_status == 'completed':
            from django.utils import timezone
            order.completed_at = timezone.now()
        
        order.save()
        
        return Response(OrderSerializer(order).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消订单"""
        order = self.get_object()
        
        # 只能取消待支付或已支付的订单
        if order.status not in ['pending', 'paid']:
            return Response(
                {"error": "当前订单状态无法取消"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 记录状态变更
        OrderStatusLog.objects.create(
            order=order,
            from_status=order.status,
            to_status='cancelled',
            notes=request.data.get('notes', '用户取消订单'),
            created_by=request.user
        )
        
        order.status = 'cancelled'
        order.save()
        
        return Response(OrderSerializer(order).data)
    
    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """支付订单（模拟支付）"""
        order = self.get_object()
        
        if order.status != 'pending':
            return Response(
                {"error": "只有待支付订单可以支付"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 模拟支付成功
        from django.utils import timezone
        import random
        import string
        
        order.is_paid = True
        order.paid_at = timezone.now()
        order.status = 'paid'
        order.transaction_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))
        order.save()
        
        # 记录状态变更
        OrderStatusLog.objects.create(
            order=order,
            from_status='pending',
            to_status='paid',
            notes='支付成功',
            created_by=request.user
        )
        
        return Response({
            "message": "支付成功",
            "transaction_id": order.transaction_id,
            "order": OrderSerializer(order).data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取订单统计信息"""
        user = request.user
        
        if user.is_staff:
            # 管理员看到所有订单统计
            total_orders = Order.objects.count()
            pending_orders = Order.objects.filter(status='pending').count()
            completed_orders = Order.objects.filter(status='completed').count()
            total_revenue = sum(order.actual_amount for order in Order.objects.filter(is_paid=True))
        else:
            # 普通用户看到自己的订单统计
            total_orders = Order.objects.filter(user=user).count()
            pending_orders = Order.objects.filter(user=user, status='pending').count()
            completed_orders = Order.objects.filter(user=user, status='completed').count()
            total_revenue = sum(order.actual_amount for order in Order.objects.filter(user=user, is_paid=True))
        
        return Response({
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "total_revenue": float(total_revenue) if total_revenue else 0
        })