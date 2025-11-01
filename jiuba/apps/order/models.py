# apps/orders/models.py
from django.db import models
from django.utils import timezone
from apps.user.models import User
from apps.shop.models import Shop
from apps.product.models import Product

class Order(models.Model):
    """订单模型 - 简化版本"""
    PAYMENT_METHOD_CHOICES = (
        ('cash', '现金支付'),
        ('points', '积分支付'),
    )
    
    # 订单基本信息
    order_number = models.CharField(max_length=50, unique=True, verbose_name="订单号")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name="用户")
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='orders', verbose_name="店铺")
    
    # 订单金额
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="现金总金额", default=0)
    total_points = models.IntegerField(default=0, verbose_name="积分总金额")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, verbose_name="支付方式")
    
    # 订单状态（只有已支付）
    is_paid = models.BooleanField(default=True, verbose_name="已支付")
    paid_at = models.DateTimeField(default=timezone.now, verbose_name="支付时间")
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name="交易号")
    
    # 时间信息
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    # 备注信息
    customer_notes = models.TextField(blank=True, verbose_name="顾客备注")
    
    class Meta:
        verbose_name = "订单"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"订单 {self.order_number}"
    
    def save(self, *args, **kwargs):
        """生成订单号"""
        if not self.order_number:
            import random
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            random_str = str(random.randint(1000, 9999))
            self.order_number = f"ORD{timestamp}{random_str}"
        
        super().save(*args, **kwargs)
    
    @property
    def item_count(self):
        """订单商品总数"""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def calculated_total_amount(self):
        """计算订单现金总金额"""
        if self.payment_method == 'cash':
            return sum(item.subtotal for item in self.items.all())
        return 0
    
    @property
    def calculated_total_points(self):
        """计算订单积分总金额"""
        if self.payment_method == 'points':
            return sum(item.points_subtotal for item in self.items.all())
        return 0

class OrderItem(models.Model):
    """订单项模型"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="订单")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="商品")
    product_name = models.CharField(max_length=100, verbose_name="商品名称")  
    product_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="商品单价")
    product_points_price = models.IntegerField(default=0, verbose_name="商品积分价格")
    quantity = models.PositiveIntegerField(default=1, verbose_name="数量")
    
    class Meta:
        verbose_name = "订单项"
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        """自动填充商品信息"""
        if self.product:
            if not self.product_name:
                self.product_name = self.product.name
            if not self.product_price:
                self.product_price = self.product.price
            if not self.product_points_price:
                self.product_points_price = self.product.points_price
        super().save(*args, **kwargs)
    
    @property
    def subtotal(self):
        """计算现金小计"""
        quantity = self.quantity or 0
        price = self.product_price or 0
        return quantity * price
    
    @property
    def points_subtotal(self):
        """计算积分小计"""
        quantity = self.quantity or 0
        points_price = self.product_points_price or 0
        return quantity * points_price