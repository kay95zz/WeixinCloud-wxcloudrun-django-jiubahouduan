from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import time
import random
from .models import Payment
from .serializers import (
    PaymentCreateSerializer, PaymentCallbackSerializer, 
    RefundSerializer, PaymentSerializer
)
from .services import WeChatPayService, BalancePayService
from apps.order.models import Order

class PaymentViewSet(viewsets.ModelViewSet):
    """
    支付视图集 - 完整的支付功能
    """
    queryset = Payment.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'create_payment':
            return PaymentCreateSerializer
        elif self.action == 'refund':
            return RefundSerializer
        elif self.action == 'wechat_callback':
            return PaymentCallbackSerializer
        return PaymentSerializer
    
    def get_queryset(self):
        """用户只能看到自己的支付记录"""
        return Payment.objects.filter(user=self.request.user).select_related('order', 'user')
    
    @action(detail=False, methods=['post'])
    def create_payment(self, request):
        """
        创建支付订单
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order_id = serializer.validated_data['order_id']
        payment_method = serializer.validated_data['payment_method']
        
        try:
            order = Order.objects.get(id=order_id, user=request.user, status='pending')
            
            # 检查是否已存在支付记录
            if hasattr(order, 'payment'):
                return Response(
                    {"error": "该订单已存在支付记录"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 生成商户订单号
            out_trade_no = self._generate_out_trade_no()
            
            # 创建支付记录
            payment = Payment.objects.create(
                order=order,
                user=request.user,
                amount=order.total_amount,
                method=payment_method,
                out_trade_no=out_trade_no,
                status='pending'
            )
            
            # 根据支付方式处理
            if payment_method == 'wechat':
                return self._process_wechat_payment(payment)
            elif payment_method == 'balance':
                return self._process_balance_payment(payment)
                    
        except Order.DoesNotExist:
            return Response(
                {"error": "订单不存在或不可支付"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _process_wechat_payment(self, payment):
        """处理微信支付"""
        wechat_service = WeChatPayService()
        result = wechat_service.unified_order(payment)
        
        if result['success']:
            return Response({
                'success': True,
                'payment_id': payment.id,
                'out_trade_no': payment.out_trade_no,
                'payment_data': result['payment_data']
            })
        else:
            payment.status = 'failed'
            payment.save()
            return Response(
                {"error": result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _process_balance_payment(self, payment):
        """处理余额支付"""
        balance_service = BalancePayService()
        result = balance_service.process_payment(payment)
        
        if result['success']:
            return Response({
                'success': True,
                'payment_id': payment.id,
                'status': 'success',
                'message': '支付成功'
            })
        else:
            return Response(
                {"error": result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def wechat_callback(self, request):
        """
        微信支付回调接口
        ---
        **模拟版本**：使用JSON格式接收回调数据
        **正式版本**：微信支付会发送XML格式数据，需要解析XML并验证签名
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        out_trade_no = serializer.validated_data['out_trade_no']
        transaction_id = serializer.validated_data['transaction_id']
        result_code = serializer.validated_data['result_code']
        
        try:
            payment = Payment.objects.get(out_trade_no=out_trade_no)
            
            if result_code == 'SUCCESS':
                # 支付成功
                payment.status = 'success'
                payment.transaction_id = transaction_id
                payment.paid_at = timezone.now()
                payment.save()
                
                # 更新订单状态
                order = payment.order
                order.status = 'paid'
                order.save()
                
                # ========== 正式微信支付回调返回格式 ==========
                # 正式版本需要返回XML格式：
                # return Response(
                #     '<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>',
                #     content_type='application/xml'
                # )
                
                return Response({'code': 'SUCCESS', 'message': '支付成功'})
            else:
                # 支付失败
                payment.status = 'failed'
                payment.save()
                return Response({'code': 'FAIL', 'message': '支付失败'})
                
        except Payment.DoesNotExist:
            return Response(
                {"error": "支付记录不存在"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def refund(self, request):
        """
        退款申请
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order_id = serializer.validated_data['order_id']
        reason = serializer.validated_data.get('reason', '')
        
        try:
            payment = Payment.objects.get(order_id=order_id, user=request.user)
            
            if payment.status != 'success':
                return Response(
                    {"error": "只有支付成功的订单才能退款"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 执行退款逻辑
            if payment.method == 'wechat':
                wechat_service = WeChatPayService()
                refund_result = wechat_service.process_refund(payment, reason)
            elif payment.method == 'balance':
                balance_service = BalancePayService()
                refund_result = balance_service.process_refund(payment, reason)
            
            if refund_result['success']:
                payment.status = 'refunded'
                payment.refunded_at = timezone.now()
                payment.save()
                
                # 更新订单状态
                order = payment.order
                order.status = 'refunded'
                order.save()
                
                return Response({'message': '退款成功'})
            else:
                return Response(
                    {"error": refund_result['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Payment.DoesNotExist:
            return Response(
                {"error": "支付记录不存在"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def query_status(self, request, pk=None):
        """
        查询支付状态
        """
        payment = self.get_object()
        
        # 如果是微信支付且状态为pending，可以查询微信支付状态
        if payment.method == 'wechat' and payment.status == 'pending':
            wechat_service = WeChatPayService()
            query_result = wechat_service.query_order(payment.out_trade_no)
            if query_result['success'] and query_result['trade_state'] == 'SUCCESS':
                payment.status = 'success'
                payment.transaction_id = query_result['transaction_id']
                payment.paid_at = timezone.now()
                payment.save()
                
                # 更新订单状态
                order = payment.order
                order.status = 'paid'
                order.save()
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data)
    
    def _generate_out_trade_no(self):
        """生成商户订单号"""
        timestamp = str(int(time.time()))
        random_str = str(random.randint(1000, 9999))
        return f"PAY{timestamp}{random_str}"