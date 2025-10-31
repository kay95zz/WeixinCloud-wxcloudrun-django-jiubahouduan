from rest_framework import serializers
from .models import Payment

class PaymentCreateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(choices=['wechat', 'balance'])

    def validate_order_id(self, value):
        from apps.order.models import Order
        user = self.context['request'].user
        try:
            order = Order.objects.get(id=value, user=user, status='pending')
        except Order.DoesNotExist:
            raise serializers.ValidationError("订单不存在或不可支付")
        return value

class PaymentCallbackSerializer(serializers.Serializer):
    """微信支付回调数据（简化）"""
    out_trade_no = serializers.CharField()
    transaction_id = serializers.CharField()
    result_code = serializers.CharField()

class RefundSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    reason = serializers.CharField(max_length=200, required=False)

# ========== 新增的序列化器 ==========
class PaymentSerializer(serializers.ModelSerializer):
    """支付记录序列化器 - 用于列表和详情展示"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'user', 'user_name', 
            'amount', 'method', 'status', 'transaction_id', 
            'out_trade_no', 'created_at', 'paid_at', 'refunded_at'
        ]
        read_only_fields = [
            'id', 'user', 'amount', 'transaction_id', 'out_trade_no',
            'created_at', 'paid_at', 'refunded_at'
        ]