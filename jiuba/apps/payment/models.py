from django.db import models
from django.utils import timezone
from apps.user.models import User
from apps.order.models import Order

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('wechat', '微信支付'),
        ('balance', '余额支付'),
    ]
    STATUS_CHOICES = [
        ('pending', '待支付'),
        ('success', '支付成功'),
        ('failed', '支付失败'),
        ('refunded', '已退款'),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment',
        verbose_name="订单"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="支付金额")
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, verbose_name="支付方式")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="支付状态")
    
    # 微信支付字段
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name="微信交易号")
    out_trade_no = models.CharField(max_length=100, unique=True, verbose_name="商户订单号")
    
    # 时间
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="支付时间")
    refunded_at = models.DateTimeField(null=True, blank=True, verbose_name="退款时间")

    class Meta:
        verbose_name = "支付记录"
        verbose_name_plural = "支付记录"
        ordering = ['-created_at']

    def __str__(self):
        return f"支付 {self.out_trade_no} - {self.get_status_display()}"