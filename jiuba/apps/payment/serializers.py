from rest_framework import serializers
from .models import Payment
from apps.order.models import Order
from apps.user.models import User

class PaymentSerializer(serializers.ModelSerializer):
    """支付记录序列化器"""
    
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    shop_name = serializers.CharField(source='order.shop.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'shop_name', 'user', 'user_name',
            'payment_method', 'payment_method_display', 'amount', 'points',
            'status', 'status_display', 'transaction_id', 'refund_amount',
            'refund_desc', 'refund_reason', 'refund_at',
            'created_at', 'paid_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'order', 'transaction_id', 'status',
            'refund_at', 'created_at', 'paid_at', 'updated_at'
        ]

class PaymentCreateSerializer(serializers.Serializer):
    """创建支付序列化器"""
    
    order_id = serializers.IntegerField(required=True)
    payment_method = serializers.ChoiceField(
        choices=['wechat', 'balance', 'points'],
        default='wechat'
    )
    openid = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_order_id(self, value):
        """验证订单ID"""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("请求上下文不存在")
        
        try:
            order = Order.objects.get(id=value, user=request.user)
            
            # 检查订单状态
            if order.is_paid:
                raise serializers.ValidationError("订单已支付")
            
            return value
        except Order.DoesNotExist:
            raise serializers.ValidationError("订单不存在")
    
    def validate(self, data):
        """验证数据"""
        payment_method = data.get('payment_method')
        openid = data.get('openid')
        
        # 微信支付需要OpenID
        if payment_method == 'wechat' and not openid:
            request = self.context.get('request')
            if request and hasattr(request.user, 'wechat_openid') and request.user.wechat_openid:
                data['openid'] = request.user.wechat_openid
            else:
                raise serializers.ValidationError({
                    "openid": "微信支付需要OpenID"
                })
        
        return data

class RefundSerializer(serializers.Serializer):
    """退款序列化器"""
    
    refund_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        required=True
    )
    refund_desc = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        default=""
    )
    refund_reason = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        default=""
    )
    
    def validate_refund_amount(self, value):
        """验证退款金额"""
        if value <= 0:
            raise serializers.ValidationError("退款金额必须大于0")
        return value

class WechatPayConfigSerializer(serializers.Serializer):
    """微信支付配置序列化器"""
    
    timeStamp = serializers.CharField(required=True)
    nonceStr = serializers.CharField(required=True)
    package = serializers.CharField(required=True)
    signType = serializers.CharField(required=True)
    paySign = serializers.CharField(required=True)
    
    class Meta:
        fields = ['timeStamp', 'nonceStr', 'package', 'signType', 'paySign']

class PaymentStatusSerializer(serializers.Serializer):
    """支付状态序列化器"""
    
    payment_status = serializers.CharField(required=True)
    order_status = serializers.CharField(required=True)
    paid_at = serializers.DateTimeField(required=False, allow_null=True)
    payment_method = serializers.CharField(required=True)
    
    class Meta:
        fields = ['payment_status', 'order_status', 'paid_at', 'payment_method']