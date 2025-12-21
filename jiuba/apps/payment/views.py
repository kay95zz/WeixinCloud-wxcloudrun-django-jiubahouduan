from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
import json
import logging

from apps.order.models import Order
from apps.user.models import User
from .models import Payment
from .serializers import PaymentSerializer, PaymentCreateSerializer, RefundSerializer
from .wechat import wechat_pay
from .services import PaymentService

logger = logging.getLogger(__name__)

class PaymentViewSet(viewsets.ModelViewSet):
    """
    支付管理 ViewSet
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """获取当前用户的支付记录"""
        return Payment.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_serializer_class(self):
        """根据请求方法返回不同的序列化器"""
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer
    
    def create(self, request):
        """
        创建支付
        """
        serializer = PaymentCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 获取订单
            order_id = serializer.validated_data['order_id']
            order = get_object_or_404(Order, id=order_id, user=request.user)
            
            # 检查订单状态
            if order.is_paid:
                return Response({
                    "success": False,
                    "message": "订单已支付"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取支付方式
            payment_method = serializer.validated_data.get('payment_method', 'wechat')
            
            # 根据支付方式处理
            if payment_method == 'wechat':
                # 获取OpenID
                openid = serializer.validated_data.get('openid')
                if not openid:
                    # 尝试从用户信息中获取
                    if hasattr(request.user, 'wechat_openid') and request.user.wechat_openid:
                        openid = request.user.wechat_openid
                    else:
                        return Response({
                            "success": False,
                            "message": "需要用户OpenID",
                            "need_openid": True
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
                
            elif payment_method == 'balance':
                # 处理余额支付
                result = PaymentService.process_balance_payment(order)
                
            elif payment_method == 'points':
                # 处理积分支付
                result = PaymentService.process_points_payment(order)
                
            else:
                return Response({
                    "success": False,
                    "message": "不支持的支付方式"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if result['success']:
                if payment_method == 'wechat':
                    return Response({
                        "success": True,
                        "payment_id": result['payment'].id,
                        "payment_config": result['payment_config'],
                        "order_number": order.order_number,
                        "message": "支付创建成功"
                    })
                else:
                    return Response({
                        "success": True,
                        "payment_id": result['payment'].id,
                        "message": "支付成功",
                        "data": result.get('balance') or result.get('points')
                    })
            else:
                return Response({
                    "success": False,
                    "message": result['message'],
                    "error_code": result.get('error_code')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"创建支付失败: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": f"创建支付失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def wechat_prepay(self, request):
        """
        微信支付统一下单
        """
        try:
            order_id = request.data.get('order_id')
            if not order_id:
                return Response({
                    "success": False,
                    "message": "订单ID不能为空"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            order = get_object_or_404(Order, id=order_id, user=request.user)
            
            # 检查订单状态
            if order.is_paid:
                return Response({
                    "success": False,
                    "message": "订单已支付"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取OpenID
            openid = request.data.get('openid')
            if not openid:
                if hasattr(request.user, 'wechat_openid') and request.user.wechat_openid:
                    openid = request.user.wechat_openid
                else:
                    return Response({
                        "success": False,
                        "message": "需要用户OpenID",
                        "need_openid": True
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
                    "payment_config": result['payment_config'],
                    "order_number": order.order_number,
                    "message": "统一下单成功"
                })
            else:
                return Response({
                    "success": False,
                    "message": result['message'],
                    "error_code": result.get('error_code')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"微信支付统一下单失败: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": f"统一下单失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        查询支付状态
        """
        try:
            payment = self.get_object()
            order = payment.order
            
            result = PaymentService.query_payment_status(order)
            
            if result['success']:
                return Response({
                    "success": True,
                    "payment_status": result['payment_status'],
                    "order_status": result['order_status'],
                    "paid_at": result['paid_at'],
                    "payment_method": result['payment_method']
                })
            else:
                return Response({
                    "success": False,
                    "message": result['message']
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"查询支付状态失败: {str(e)}")
            return Response({
                "success": False,
                "message": f"查询支付状态失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """
        申请退款
        """
        try:
            payment = self.get_object()
            
            # 验证用户权限
            if payment.user != request.user and not request.user.is_staff:
                return Response({
                    "success": False,
                    "message": "无权操作此支付记录"
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = RefundSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            refund_amount = serializer.validated_data['refund_amount']
            refund_desc = serializer.validated_data.get('refund_desc', '')
            refund_reason = serializer.validated_data.get('refund_reason', '')
            
            # 处理退款
            result = PaymentService.process_refund(
                order=payment.order,
                refund_amount=refund_amount,
                refund_desc=refund_desc,
                refund_reason=refund_reason
            )
            
            if result['success']:
                return Response({
                    "success": True,
                    "refund_id": result.get('refund_id'),
                    "message": result['message'],
                    "data": result.get('balance') or result.get('points')
                })
            else:
                return Response({
                    "success": False,
                    "message": result['message']
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"申请退款失败: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": f"申请退款失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def order_payments(self, request):
        """
        获取订单的支付记录
        """
        try:
            order_id = request.query_params.get('order_id')
            if not order_id:
                return Response({
                    "success": False,
                    "message": "订单ID不能为空"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            order = get_object_or_404(Order, id=order_id, user=request.user)
            payments = Payment.objects.filter(order=order).order_by('-created_at')
            
            serializer = self.get_serializer(payments, many=True)
            
            return Response({
                "success": True,
                "data": serializer.data,
                "order_status": order.status,
                "is_paid": order.is_paid
            })
            
        except Exception as e:
            logger.error(f"获取订单支付记录失败: {str(e)}")
            return Response({
                "success": False,
                "message": f"获取支付记录失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
def wechat_pay_callback(request):
    """
    微信支付回调接口 - 修复版
    注意：微信云托管会调用此接口通知支付结果
    必须返回 {"errcode": 0, "errmsg": "OK"}，否则会重复回调
    """
    try:
        # 解析回调数据
        if request.content_type == 'application/json':
            callback_data = request.data
        else:
            try:
                callback_data = json.loads(request.body.decode('utf-8'))
            except:
                callback_data = request.POST.dict()
        
        logger.info(f"💰 微信支付回调原始数据: {json.dumps(callback_data, ensure_ascii=False)}")
        
        # 检查必要字段
        return_code = callback_data.get('return_code')
        result_code = callback_data.get('result_code')
        out_trade_no = callback_data.get('out_trade_no')
        
        if not out_trade_no:
            logger.error("❌ 支付回调中未找到订单号")
            # 仍然返回成功，避免重复回调
            return JsonResponse({"errcode": 0, "errmsg": "OK"})
        
        # 查找订单
        order = Order.objects.filter(order_number=out_trade_no).first()
        if not order:
            logger.error(f"❌ 订单不存在: {out_trade_no}")
            return JsonResponse({"errcode": 0, "errmsg": "OK"})
        
        # 根据回调结果处理
        if return_code == 'SUCCESS' and result_code == 'SUCCESS':
            # 支付成功
            transaction_id = callback_data.get('transaction_id')
            
            with transaction.atomic():
                # 查找支付记录
                payment = Payment.objects.filter(order=order, payment_method='wechat', status='pending').first()
                
                if payment:
                    # 更新支付记录
                    payment.status = 'paid'
                    payment.paid_at = timezone.now()
                    payment.transaction_id = transaction_id
                    payment.save()
                    
                    # 更新订单状态
                    order.is_paid = True
                    order.paid_at = payment.paid_at
                    order.payment_method = 'wechat'
                    order.transaction_id = transaction_id
                    order.save()
                    
                    logger.info(f"✅ 支付回调处理成功: order_id={order.id}, payment_id={payment.id}")
                else:
                    # 如果没有支付记录，创建一个
                    payment = Payment.objects.create(
                        user=order.user,
                        order=order,
                        payment_method='wechat',
                        amount=order.total_amount,
                        status='paid',
                        paid_at=timezone.now(),
                        transaction_id=transaction_id
                    )
                    logger.info(f"✅ 创建新的支付记录: order_id={order.id}, payment_id={payment.id}")
        
        # 必须返回成功响应
        return JsonResponse({"errcode": 0, "errmsg": "OK"})
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ 回调数据JSON解析失败: {str(e)}")
        return JsonResponse({"errcode": 0, "errmsg": "OK"})
    except Exception as e:
        logger.error(f"❌ 支付回调处理异常: {str(e)}", exc_info=True)
        return JsonResponse({"errcode": 0, "errmsg": "OK"})

class WechatPayCheckView(APIView):
    """微信支付检查视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        检查微信支付状态
        """
        try:
            order_id = request.data.get('order_id')
            if not order_id:
                return Response({
                    "success": False,
                    "message": "订单ID不能为空"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            order = get_object_or_404(Order, id=order_id, user=request.user)
            
            # 查询微信支付状态
            result = wechat_pay.query_order(out_trade_no=order.order_number)
            
            if not result['success']:
                return Response({
                    "success": False,
                    "message": result['message']
                }, status=status.HTTP_400_BAD_REQUEST)
            
            trade_state = result.get('trade_state')
            trade_state_desc = result.get('trade_state_desc')
            
            response_data = {
                "success": True,
                "trade_state": trade_state,
                "trade_state_desc": trade_state_desc,
                "order_status": order.status,
                "is_paid": order.is_paid
            }
            
            # 如果支付成功，更新订单状态
            if trade_state == 'SUCCESS' and not order.is_paid:
                transaction_id = result['data'].get('transaction_id')
                
                payment = Payment.objects.filter(order=order, payment_method='wechat', status='pending').first()
                if payment:
                    PaymentService.update_payment_success(payment, transaction_id)
                    response_data['order_status'] = 'paid'
                    response_data['is_paid'] = True
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"检查微信支付状态失败: {str(e)}")
            return Response({
                "success": False,
                "message": f"检查支付状态失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)