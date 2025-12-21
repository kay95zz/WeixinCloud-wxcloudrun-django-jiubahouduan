"""
订单视图模块
"""
import logging
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Count
from datetime import timedelta

from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Order, OrderItem
# 根据你的 apps/order/serializers.py 文件，正确的导入应该是：
from .serializers import OrderSerializer, CreateOrderSerializer, OrderListSerializer
from apps.payment.services import PaymentService
from apps.payment.wechat import wechat_pay
from apps.user.models import User
from apps.product.models import Product
from apps.shop.models import Shop

logger = logging.getLogger(__name__)

class OrderViewSet(viewsets.ModelViewSet):
    """
    订单管理 ViewSet
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['order_number', 'customer_notes']
    ordering_fields = ['created_at', 'total_amount', 'paid_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """获取当前用户的订单"""
        queryset = Order.objects.filter(user=self.request.user)
        
        # 状态筛选
        status_filter = self.request.query_params.get('status')
        if status_filter:
            if status_filter == 'unpaid':
                queryset = queryset.filter(is_paid=False)
            elif status_filter == 'paid':
                queryset = queryset.filter(is_paid=True)
            elif status_filter == 'cancelled':
                queryset = queryset.filter(is_cancelled=True)
        
        # 店铺筛选
        shop_id = self.request.query_params.get('shop_id')
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)
        
        # 时间范围筛选
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.select_related('shop', 'user')
    
    def get_serializer_class(self):
        """根据请求方法返回不同的序列化器"""
        if self.action == 'create':
            return CreateOrderSerializer  # 注意：是CreateOrderSerializer不是OrderCreateSerializer
        elif self.action == 'retrieve':
            return OrderSerializer  # 使用OrderSerializer代替不存在的OrderDetailSerializer
        return OrderSerializer
    
    def create(self, request):
        """
        创建订单 - 简化版
        注意：根据你的CreateOrderSerializer，需要shop_id、customer_notes、payment_method字段
        """
        serializer = CreateOrderSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                # 获取数据
                shop_id = serializer.validated_data['shop_id']
                customer_notes = serializer.validated_data.get('customer_notes', '')
                payment_method = serializer.validated_data.get('payment_method', 'wechat')
                
                # 获取店铺
                shop = get_object_or_404(Shop, id=shop_id, is_active=True)
                
                # 创建订单
                order = Order.objects.create(
                    user=request.user,
                    shop=shop,
                    customer_notes=customer_notes,
                    payment_method=payment_method,
                    total_amount=0,
                    total_points=0
                )
                
                logger.info(f"订单创建成功: order_id={order.id}, order_number={order.order_number}")
                
                return Response({
                    "success": True,
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "message": "订单创建成功，请添加商品"
                })
                
        except Exception as e:
            logger.error(f"创建订单失败: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": f"创建订单失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """添加商品到订单"""
        try:
            order = self.get_object()
            
            # 验证订单状态
            if order.is_paid:
                return Response({
                    "success": False,
                    "message": "订单已支付，无法添加商品"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1)
            
            if not product_id:
                return Response({
                    "success": False,
                    "message": "需要提供product_id"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            product = get_object_or_404(
                Product,
                id=product_id,
                shop=order.shop,
                is_available=True,
                status='published'
            )
            
            # 检查库存
            if product.stock_quantity < quantity:
                return Response({
                    "success": False,
                    "message": f"商品 {product.name} 库存不足"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                # 创建或更新订单项
                order_item, created = OrderItem.objects.get_or_create(
                    order=order,
                    product=product,
                    defaults={
                        'quantity': quantity,
                        'product_name': product.name,
                        'product_price': product.price,
                        'product_points_price': product.points_price
                    }
                )
                
                if not created:
                    order_item.quantity += quantity
                    order_item.save()
                
                # 更新订单金额
                order.total_amount = sum(item.subtotal for item in order.items.all())
                order.total_points = sum(item.points_subtotal for item in order.items.all())
                order.save()
                
                # 减少库存
                product.stock_quantity -= quantity
                product.save()
                
                return Response({
                    "success": True,
                    "message": "商品添加成功",
                    "order_item_id": order_item.id,
                    "total_amount": float(order.total_amount),
                    "total_points": order.total_points
                })
                
        except Exception as e:
            logger.error(f"添加商品失败: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": f"添加商品失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def remove_item(self, request, pk=None):
        """从订单移除商品"""
        try:
            order = self.get_object()
            
            if order.is_paid:
                return Response({
                    "success": False,
                    "message": "订单已支付，无法移除商品"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            item_id = request.data.get('item_id')
            if not item_id:
                return Response({
                    "success": False,
                    "message": "需要提供item_id"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            order_item = get_object_or_404(OrderItem, id=item_id, order=order)
            
            with transaction.atomic():
                # 恢复库存
                product = order_item.product
                product.stock_quantity += order_item.quantity
                product.save()
                
                # 移除订单项
                order_item.delete()
                
                # 更新订单金额
                order.total_amount = sum(item.subtotal for item in order.items.all())
                order.total_points = sum(item.points_subtotal for item in order.items.all())
                order.save()
                
                return Response({
                    "success": True,
                    "message": "商品移除成功",
                    "total_amount": float(order.total_amount),
                    "total_points": order.total_points
                })
                
        except Exception as e:
            logger.error(f"移除商品失败: {str(e)}")
            return Response({
                "success": False,
                "message": f"移除商品失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """
        支付订单
        支持微信支付、余额支付、积分支付
        """
        try:
            order = self.get_object()
            
            # 检查订单状态
            if order.is_paid:
                return Response({
                    "success": False,
                    "message": "订单已支付",
                    "code": "ORDER_ALREADY_PAID"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if order.is_cancelled:
                return Response({
                    "success": False,
                    "message": "订单已取消，无法支付",
                    "code": "ORDER_CANCELLED"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 检查订单是否有商品
            if order.items.count() == 0:
                return Response({
                    "success": False,
                    "message": "订单没有商品，无法支付",
                    "code": "EMPTY_ORDER"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取支付方式
            payment_method = request.data.get('payment_method', 'wechat')
            
            if payment_method == 'wechat':
                return self._pay_with_wechat(order, request)
            elif payment_method == 'balance':
                return self._pay_with_balance(order, request)
            elif payment_method == 'points':
                return self._pay_with_points(order, request)
            else:
                return Response({
                    "success": False,
                    "message": "不支持的支付方式",
                    "code": "INVALID_PAYMENT_METHOD"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"支付订单失败: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": f"支付失败: {str(e)}",
                "code": "PAYMENT_ERROR"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _pay_with_wechat(self, order, request):
        """
        微信支付处理
        """
        try:
            # 检查微信支付是否启用
            from django.conf import settings
            if not hasattr(settings, 'WECHAT_MERCHANT_ID') or not settings.WECHAT_MERCHANT_ID:
                return Response({
                    "success": False,
                    "message": "微信支付未配置",
                    "code": "WECHAT_PAY_NOT_CONFIGURED"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取OpenID
            openid = request.data.get('openid')
            if not openid:
                # 尝试从用户信息中获取
                if hasattr(request.user, 'wechat_openid') and request.user.wechat_openid:
                    openid = request.user.wechat_openid
                else:
                    return Response({
                        "success": False,
                        "message": "需要用户OpenID",
                        "need_openid": True,
                        "code": "OPENID_REQUIRED"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取客户端IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(',')[0]
            else:
                client_ip = request.META.get('REMOTE_ADDR')
            
            # 处理微信支付
            result = PaymentService.process_wechat_payment(
                order=order,
                openid=openid,
                client_ip=client_ip or '127.0.0.1'
            )
            
            if result['success']:
                return Response({
                    "success": True,
                    "payment_id": result.get('payment', {}).id if result.get('payment') else None,
                    "payment_config": result.get('payment_config', {}),
                    "order_number": order.order_number,
                    "message": "统一下单成功"
                })
            else:
                return Response({
                    "success": False,
                    "message": result.get('message', '微信支付失败'),
                    "error_code": result.get('error_code'),
                    "code": "WECHAT_PAY_FAILED"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"微信支付处理失败: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": f"微信支付处理失败: {str(e)}",
                "code": "WECHAT_PAY_PROCESS_ERROR"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _pay_with_balance(self, order, request):
        """
        余额支付处理
        """
        try:
            # 检查订单是否支持余额支付
            if order.total_amount <= 0:
                return Response({
                    "success": False,
                    "message": "订单金额为0，无法使用余额支付",
                    "code": "ZERO_AMOUNT_ORDER"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 处理余额支付
            result = PaymentService.process_balance_payment(order)
            
            if result['success']:
                return Response({
                    "success": True,
                    "payment_id": result.get('payment', {}).id if result.get('payment') else None,
                    "order_number": order.order_number,
                    "balance": result.get('balance', 0),
                    "message": "余额支付成功"
                })
            else:
                return Response({
                    "success": False,
                    "message": result.get('message', '余额支付失败'),
                    "code": "BALANCE_PAY_FAILED"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"余额支付处理失败: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": f"余额支付处理失败: {str(e)}",
                "code": "BALANCE_PAY_PROCESS_ERROR"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _pay_with_points(self, order, request):
        """
        积分支付处理
        """
        try:
            # 检查订单是否支持积分支付
            if order.total_points <= 0:
                return Response({
                    "success": False,
                    "message": "该订单不支持积分支付",
                    "code": "POINTS_PAY_NOT_SUPPORTED"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 处理积分支付
            result = PaymentService.process_points_payment(order)
            
            if result['success']:
                return Response({
                    "success": True,
                    "payment_id": result.get('payment', {}).id if result.get('payment') else None,
                    "order_number": order.order_number,
                    "points": result.get('points', 0),
                    "message": "积分支付成功"
                })
            else:
                return Response({
                    "success": False,
                    "message": result.get('message', '积分支付失败'),
                    "code": "POINTS_PAY_FAILED"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"积分支付处理失败: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": f"积分支付处理失败: {str(e)}",
                "code": "POINTS_PAY_PROCESS_ERROR"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def payment_status(self, request, pk=None):
        """
        查询订单支付状态
        """
        try:
            order = self.get_object()
            
            result = PaymentService.query_payment_status(order)
            
            if result['success']:
                return Response({
                    "success": True,
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "payment_status": result.get('payment_status', 'unknown'),
                    "order_status": result.get('order_status', 'unknown'),
                    "paid_at": result.get('paid_at'),
                    "payment_method": result.get('payment_method', 'unknown'),
                    "is_paid": order.is_paid
                })
            else:
                return Response({
                    "success": False,
                    "message": result.get('message', '查询失败'),
                    "code": "PAYMENT_STATUS_QUERY_FAILED"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"查询支付状态失败: {str(e)}")
            return Response({
                "success": False,
                "message": f"查询支付状态失败: {str(e)}",
                "code": "PAYMENT_STATUS_QUERY_ERROR"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        取消订单
        """
        try:
            order = self.get_object()
            
            # 检查订单状态
            if order.is_paid:
                return Response({
                    "success": False,
                    "message": "订单已支付，无法取消",
                    "code": "ORDER_ALREADY_PAID"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if order.is_cancelled:
                return Response({
                    "success": False,
                    "message": "订单已取消",
                    "code": "ORDER_ALREADY_CANCELLED"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                # 恢复库存
                for item in order.items.all():
                    product = item.product
                    product.stock_quantity += item.quantity
                    product.save()
                
                # 更新订单状态
                order.is_cancelled = True
                order.save()
                
                # 如果有待支付的支付记录，关闭它
                from apps.payment.models import Payment
                payment = Payment.objects.filter(
                    order=order,
                    status='pending',
                    payment_method='wechat'
                ).first()
                
                if payment:
                    payment.status = 'closed'
                    payment.save()
                    
                    # 尝试关闭微信支付订单
                    try:
                        wechat_pay.close_order(order.order_number)
                    except:
                        pass
                
                logger.info(f"订单取消成功: order_id={order.id}")
                
                return Response({
                    "success": True,
                    "message": "订单取消成功"
                })
                
        except Exception as e:
            logger.error(f"取消订单失败: {str(e)}")
            return Response({
                "success": False,
                "message": f"取消订单失败: {str(e)}",
                "code": "ORDER_CANCEL_ERROR"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)