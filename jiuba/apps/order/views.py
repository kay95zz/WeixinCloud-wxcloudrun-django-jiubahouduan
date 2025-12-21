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
            return CreateOrderSerializer  # 修复：改为 CreateOrderSerializer
        elif self.action == 'retrieve':
            return OrderSerializer  # 修复：使用 OrderSerializer 代替不存在的 OrderDetailSerializer
        return OrderSerializer
    
    def create(self, request):
        """
        创建订单
        """
        serializer = CreateOrderSerializer(data=request.data, context={'request': request})  # 修复：改为 CreateOrderSerializer
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
    
    def _process_immediate_payment(self, order, payment_method):
        """处理立即支付（积分、余额）"""
        if payment_method == 'balance':
            return PaymentService.process_balance_payment(order)
        elif payment_method == 'points':
            return PaymentService.process_points_payment(order)
        return {"success": True, "message": "无需立即支付"}
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """添加商品到订单"""
        try:
            order = self.get_object()
            
            # 验证订单状态
            if order.is_paid:
                return Response({
                    "success": False,
                    "message": "订单已支付，无法添加商品",
                    "code": "ORDER_ALREADY_PAID"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1)
            
            if not product_id:
                return Response({
                    "success": False,
                    "message": "需要提供product_id",
                    "code": "MISSING_PRODUCT_ID"
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
                    "message": f"商品 {product.name} 库存不足",
                    "code": "INSUFFICIENT_STOCK"
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
                "message": f"添加商品失败: {str(e)}",
                "code": "ADD_ITEM_ERROR"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def remove_item(self, request, pk=None):
        """从订单移除商品"""
        try:
            order = self.get_object()
            
            if order.is_paid:
                return Response({
                    "success": False,
                    "message": "订单已支付，无法移除商品",
                    "code": "ORDER_ALREADY_PAID"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            item_id = request.data.get('item_id')
            if not item_id:
                return Response({
                    "success": False,
                    "message": "需要提供item_id",
                    "code": "MISSING_ITEM_ID"
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
                "message": f"移除商品失败: {str(e)}",
                "code": "REMOVE_ITEM_ERROR"
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
    def refund(self, request, pk=None):
        """
        申请退款
        """
        try:
            order = self.get_object()
            
            # 检查权限
            if order.user != request.user and not request.user.is_staff:
                return Response({
                    "success": False,
                    "message": "无权操作此订单",
                    "code": "PERMISSION_DENIED"
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 检查订单状态
            if not order.is_paid:
                return Response({
                    "success": False,
                    "message": "订单未支付，无法退款",
                    "code": "ORDER_NOT_PAID"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 检查订单是否已取消
            if order.is_cancelled:
                return Response({
                    "success": False,
                    "message": "订单已取消，无法退款",
                    "code": "ORDER_CANCELLED"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取退款参数
            refund_amount = request.data.get('refund_amount')
            if not refund_amount:
                # 默认全额退款
                refund_amount = order.total_amount
            
            refund_desc = request.data.get('refund_desc', '用户申请退款')
            refund_reason = request.data.get('refund_reason', '')
            
            # 处理退款
            result = PaymentService.process_refund(
                order=order,
                refund_amount=refund_amount,
                refund_desc=refund_desc,
                refund_reason=refund_reason
            )
            
            if result['success']:
                return Response({
                    "success": True,
                    "refund_id": result.get('refund_id'),
                    "order_number": order.order_number,
                    "refund_amount": float(refund_amount),
                    "message": result.get('message', '退款申请成功')
                })
            else:
                return Response({
                    "success": False,
                    "message": result.get('message', '退款失败'),
                    "code": "REFUND_FAILED"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"申请退款失败: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": f"申请退款失败: {str(e)}",
                "code": "REFUND_PROCESS_ERROR"
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
    
    @action(detail=False, methods=['get'])
    def payment_methods(self, request):
        """
        获取支持的支付方式
        """
        try:
            order_id = request.query_params.get('order_id')
            payment_methods = []
            
            if order_id:
                order = get_object_or_404(Order, id=order_id, user=request.user)
                
                # 微信支付
                from django.conf import settings
                if hasattr(settings, 'WECHAT_MERCHANT_ID') and settings.WECHAT_MERCHANT_ID:
                    payment_methods.append({
                        "code": "wechat",
                        "name": "微信支付",
                        "icon": "wechat",
                        "description": "使用微信支付完成付款"
                    })
                
                # 余额支付
                payment_methods.append({
                    "code": "balance",
                    "name": "余额支付",
                    "icon": "wallet",
                    "description": f"使用账户余额支付（当前余额：¥{request.user.balance:.2f}）",
                    "available": float(request.user.balance) >= float(order.total_amount),
                    "balance_required": float(order.total_amount)
                })
                
                # 积分支付（如果订单支持）
                if order.total_points > 0:
                    payment_methods.append({
                        "code": "points",
                        "name": "积分支付",
                        "icon": "points",
                        "description": f"使用积分支付（需要积分：{order.total_points}）",
                        "available": request.user.points >= order.total_points,
                        "points_required": order.total_points
                    })
            else:
                # 如果没有订单ID，返回所有支持的支付方式
                from django.conf import settings
                if hasattr(settings, 'WECHAT_MERCHANT_ID') and settings.WECHAT_MERCHANT_ID:
                    payment_methods.append({
                        "code": "wechat",
                        "name": "微信支付",
                        "icon": "wechat",
                        "description": "使用微信支付完成付款"
                    })
                
                payment_methods.append({
                    "code": "balance",
                    "name": "余额支付",
                    "icon": "wallet",
                    "description": f"使用账户余额支付（当前余额：¥{request.user.balance:.2f}）"
                })
                
                payment_methods.append({
                    "code": "points",
                    "name": "积分支付",
                    "icon": "points",
                    "description": "使用积分支付"
                })
            
            return Response({
                "success": True,
                "payment_methods": payment_methods
            })
            
        except Exception as e:
            logger.error(f"获取支付方式失败: {str(e)}")
            return Response({
                "success": False,
                "message": f"获取支付方式失败: {str(e)}",
                "code": "PAYMENT_METHODS_QUERY_ERROR"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def cancel_payment(self, request, pk=None):
        """
        取消支付（关闭支付订单）
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
            
            # 查找待支付的支付记录
            from apps.payment.models import Payment
            payment = Payment.objects.filter(
                order=order,
                status='pending',
                payment_method='wechat'
            ).first()
            
            if payment:
                # 如果是微信支付，尝试关闭订单
                result = wechat_pay.close_order(order.order_number)
                
                if result and result.get('success'):
                    payment.status = 'closed'
                    payment.save()
                    
                    return Response({
                        "success": True,
                        "message": "支付已取消"
                    })
                else:
                    # 如果关闭失败，直接标记为关闭
                    payment.status = 'closed'
                    payment.save()
                    
                    return Response({
                        "success": True,
                        "message": "支付已取消"
                    })
            else:
                return Response({
                    "success": False,
                    "message": "未找到待支付的记录",
                    "code": "NO_PENDING_PAYMENT"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"取消支付失败: {str(e)}")
            return Response({
                "success": False,
                "message": f"取消支付失败: {str(e)}",
                "code": "CANCEL_PAYMENT_ERROR"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def retry_payment(self, request, pk=None):
        """
        重新支付（对于失败的支付）
        """
        try:
            order = self.get_object()
            
            # 检查订单状态
            if order.is_paid:
                return Response({
                    "success": False,
                    "message": "订单已支付，无需重新支付",
                    "code": "ORDER_ALREADY_PAID"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 查找失败的支付记录
            from apps.payment.models import Payment
            payment = Payment.objects.filter(
                order=order,
                status='failed',
                payment_method='wechat'
            ).first()
            
            if payment:
                # 标记支付记录为关闭
                payment.status = 'closed'
                payment.save()
            
            # 返回支付方式列表，让用户重新选择
            return Response({
                "success": True,
                "message": "请选择支付方式重新支付",
                "order_id": order.id,
                "order_number": order.order_number
            })
            
        except Exception as e:
            logger.error(f"重新支付处理失败: {str(e)}")
            return Response({
                "success": False,
                "message": f"重新支付处理失败: {str(e)}",
                "code": "RETRY_PAYMENT_ERROR"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def payment_statistics(self, request):
        """
        获取支付统计信息（商家用）
        """
        try:
            # 检查用户权限
            if not request.user.is_staff:
                return Response({
                    "success": False,
                    "message": "无权访问此数据",
                    "code": "PERMISSION_DENIED"
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 时间范围
            today = timezone.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # 今日统计
            today_stats = Order.objects.filter(
                is_paid=True,
                paid_at__date=today
            ).aggregate(
                count=Count('id'),
                amount=Sum('total_amount'),
                wechat_count=Count('id', filter=Q(payment_method='wechat')),
                balance_count=Count('id', filter=Q(payment_method='balance')),
                points_count=Count('id', filter=Q(payment_method='points'))
            )
            
            # 本周统计
            week_stats = Order.objects.filter(
                is_paid=True,
                paid_at__date__gte=week_ago
            ).aggregate(
                count=Count('id'),
                amount=Sum('total_amount')
            )
            
            # 本月统计
            month_stats = Order.objects.filter(
                is_paid=True,
                paid_at__date__gte=month_ago
            ).aggregate(
                count=Count('id'),
                amount=Sum('total_amount')
            )
            
            # 支付方式统计
            payment_method_stats = Order.objects.filter(
                is_paid=True
            ).values('payment_method').annotate(
                count=Count('id'),
                amount=Sum('total_amount')
            ).order_by('-amount')
            
            return Response({
                "success": True,
                "today": {
                    "count": today_stats['count'] or 0,
                    "amount": float(today_stats['amount'] or 0),
                    "wechat_count": today_stats['wechat_count'] or 0,
                    "balance_count": today_stats['balance_count'] or 0,
                    "points_count": today_stats['points_count'] or 0
                },
                "week": {
                    "count": week_stats['count'] or 0,
                    "amount": float(week_stats['amount'] or 0)
                },
                "month": {
                    "count": month_stats['count'] or 0,
                    "amount": float(month_stats['amount'] or 0)
                },
                "payment_methods": list(payment_method_stats)
            })
            
        except Exception as e:
            logger.error(f"获取支付统计失败: {str(e)}")
            return Response({
                "success": False,
                "message": f"获取支付统计失败: {str(e)}",
                "code": "PAYMENT_STATISTICS_ERROR"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        订单汇总统计（用户用）
        """
        try:
            user = request.user
            
            # 订单统计
            stats = Order.objects.filter(user=user).aggregate(
                total=Count('id'),
                unpaid=Count('id', filter=Q(is_paid=False, is_cancelled=False)),
                paid=Count('id', filter=Q(is_paid=True)),
                cancelled=Count('id', filter=Q(is_cancelled=True))
            )
            
            # 今日订单
            today_orders = Order.objects.filter(
                user=user,
                created_at__date=timezone.now().date()
            ).count()
            
            # 最近一周消费
            week_ago = timezone.now().date() - timedelta(days=7)
            week_spending = Order.objects.filter(
                user=user,
                is_paid=True,
                paid_at__date__gte=week_ago
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            return Response({
                "success": True,
                "stats": {
                    "total": stats['total'] or 0,
                    "unpaid": stats['unpaid'] or 0,
                    "paid": stats['paid'] or 0,
                    "cancelled": stats['cancelled'] or 0,
                    "today": today_orders,
                    "week_spending": float(week_spending)
                }
            })
            
        except Exception as e:
            logger.error(f"获取订单汇总失败: {str(e)}")
            return Response({
                "success": False,
                "message": f"获取订单汇总失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)