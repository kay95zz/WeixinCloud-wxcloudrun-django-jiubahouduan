from django.db import models
from django.utils import timezone
from apps.user.models import User
from apps.shop.models import Shop
from apps.product.models import Product

class Order(models.Model):
    """订单模型"""
    STATUS_CHOICES = (
        ('pending', '待支付'),
        ('paid', '已支付'),
        ('confirmed', '已确认'),
        ('preparing', '准备中'),
        ('ready', '已就绪'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('refunded', '已退款'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('wechat', '微信支付'),
        ('balance', '余额支付'),
        ('cash', '现金支付'),
    )
    
    # 订单基本信息
    order_number = models.CharField(max_length=50, unique=True, verbose_name="订单号")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name="用户")
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='orders', verbose_name="店铺")
    
    # 订单金额
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="订单总金额")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="优惠金额")
    actual_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="实付金额")
    
    # 订单状态
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="订单状态")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, verbose_name="支付方式", blank=True)
    
    # 支付信息
    is_paid = models.BooleanField(default=False, verbose_name="是否支付")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="支付时间")
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name="交易号")
    
    # 时间信息
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    
    # 备注信息
    customer_notes = models.TextField(blank=True, verbose_name="顾客备注")
    admin_notes = models.TextField(blank=True, verbose_name="管理员备注")
    
    class Meta:
        verbose_name = "订单"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"订单 {self.order_number}"
    
    def save(self, *args, **kwargs):
        """生成订单号"""
        if not self.order_number:
            # 生成订单号：时间戳 + 随机数
            import random
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            random_str = str(random.randint(1000, 9999))
            self.order_number = f"ORD{timestamp}{random_str}"
        
        # 计算实付金额
        total = self.total_amount or 0
        discount = self.discount_amount or 0
        self.actual_amount = total - discount
        
        super().save(*args, **kwargs)
    
    @property
    def item_count(self):
        """订单商品总数"""
        return sum(item.quantity for item in self.items.all())

class OrderItem(models.Model):
    """订单项模型"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="订单")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="商品")
    product_name = models.CharField(max_length=100, verbose_name="商品名称")  # 保存下单时的商品名称
    product_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="商品单价")
    quantity = models.PositiveIntegerField(default=1, verbose_name="数量")
    
    class Meta:
        verbose_name = "订单项"
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    @property
    def subtotal(self):
        """计算单项小计"""
        subquantity = self.quantity or 0
        subproductprice = self.quantity or 0
        #return self.quantity * self.product_price
        return subquantity * subproductprice

class OrderStatusLog(models.Model):
    """订单状态日志"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_logs', verbose_name="订单")
    from_status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, verbose_name="原状态")
    to_status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, verbose_name="新状态")
    notes = models.TextField(blank=True, verbose_name="备注")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="操作人")
    
    class Meta:
        verbose_name = "订单状态日志"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.from_status} -> {self.to_status}"