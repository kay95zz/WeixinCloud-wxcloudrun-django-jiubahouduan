from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from apps.user.models import User
from apps.order.models import Order

class Payment(models.Model):
    """支付记录模型"""
    
    PAYMENT_METHODS = [
        ('wechat', '微信支付'),
        ('balance', '余额支付'),
        ('points', '积分支付'),
        ('cash', '现金支付'),
        ('alipay', '支付宝'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待支付'),
        ('paid', '已支付'),
        ('refunding', '退款中'),
        ('refunded', '已退款'),
        ('failed', '支付失败'),
        ('closed', '已关闭'),
        ('cancelled', '已取消'),
    ]
    
    # 基本信息
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="用户",
        related_name="payments"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name="订单",
        related_name="payments"
    )
    payment_method = models.CharField(
        "支付方式",
        max_length=20,
        choices=PAYMENT_METHODS,
        default='wechat'
    )
    
    # 支付金额
    amount = models.DecimalField(
        "支付金额",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    points = models.IntegerField(
        "支付积分",
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # 支付状态
    status = models.CharField(
        "支付状态",
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    transaction_id = models.CharField(
        "交易号",
        max_length=100,
        blank=True,
        null=True,
        db_index=True
    )
    
    # 支付数据（存储支付配置、回调数据等）
    payment_data = models.TextField(
        "支付数据",
        blank=True,
        null=True,
        help_text="存储支付配置、回调数据等JSON格式数据"
    )
    extra_data = models.TextField(
        "额外数据",
        blank=True,
        null=True,
        help_text="存储额外的支付相关数据"
    )
    
    # 退款相关
    refund_amount = models.DecimalField(
        "退款金额",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    refund_desc = models.TextField(
        "退款说明",
        blank=True,
        null=True
    )
    refund_reason = models.CharField(
        "退款原因",
        max_length=200,
        blank=True,
        null=True
    )
    refund_at = models.DateTimeField(
        "退款时间",
        blank=True,
        null=True
    )
    
    # 错误信息
    error_code = models.CharField(
        "错误代码",
        max_length=50,
        blank=True,
        null=True
    )
    error_message = models.TextField(
        "错误信息",
        blank=True,
        null=True
    )
    
    # 时间戳
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    paid_at = models.DateTimeField("支付时间", blank=True, null=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    
    class Meta:
        verbose_name = "支付记录"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['order', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.order.order_number} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        """保存前自动更新一些字段"""
        # 如果是支付成功状态，设置支付时间
        if self.status == 'paid' and not self.paid_at:
            self.paid_at = timezone.now()
        
        # 如果是退款成功状态，设置退款时间
        if self.status == 'refunded' and not self.refund_at:
            self.refund_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def is_success(self):
        """是否支付成功"""
        return self.status == 'paid'
    
    @property
    def is_pending(self):
        """是否待支付"""
        return self.status == 'pending'
    
    @property
    def is_refunded(self):
        """是否已退款"""
        return self.status == 'refunded'
    
    @property
    def can_refund(self):
        """是否可以退款"""
        return self.status == 'paid' and self.refund_amount < self.amount
    
    @property
    def formatted_amount(self):
        """格式化金额"""
        return f"¥{self.amount:.2f}"
    
    @property
    def formatted_refund_amount(self):
        """格式化退款金额"""
        if self.refund_amount > 0:
            return f"¥{self.refund_amount:.2f}"
        return "-"
    
    def get_payment_data_dict(self):
        """获取支付数据字典"""
        import json
        if self.payment_data:
            try:
                return json.loads(self.payment_data)
            except:
                return {}
        return {}
    
    def get_extra_data_dict(self):
        """获取额外数据字典"""
        import json
        if self.extra_data:
            try:
                return json.loads(self.extra_data)
            except:
                return {}
        return {}
    
    def set_payment_data(self, data):
        """设置支付数据"""
        import json
        self.payment_data = json.dumps(data, ensure_ascii=False)
    
    def set_extra_data(self, data):
        """设置额外数据"""
        import json
        self.extra_data = json.dumps(data, ensure_ascii=False)
    
    def mark_as_paid(self, transaction_id=None):
        """标记为已支付"""
        self.status = 'paid'
        self.paid_at = timezone.now()
        if transaction_id:
            self.transaction_id = transaction_id
        self.save()
    
    def mark_as_refunding(self, refund_amount, refund_desc="", refund_reason=""):
        """标记为退款中"""
        self.status = 'refunding'
        self.refund_amount = refund_amount
        self.refund_desc = refund_desc
        self.refund_reason = refund_reason
        self.save()
    
    def mark_as_refunded(self):
        """标记为已退款"""
        self.status = 'refunded'
        self.refund_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, error_code="", error_message=""):
        """标记为失败"""
        self.status = 'failed'
        self.error_code = error_code
        self.error_message = error_message
        self.save()
    
    def mark_as_closed(self):
        """标记为已关闭"""
        self.status = 'closed'
        self.save()