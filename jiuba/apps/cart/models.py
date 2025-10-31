from django.db import models
from django.utils import timezone
from apps.user.models import User
from apps.shop.models import Shop
from apps.product.models import Product

class Cart(models.Model):
    """购物车模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name="店铺")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "购物车"
        verbose_name_plural = verbose_name
        unique_together = ('user', 'shop')  # 一个用户在一个店铺只能有一个购物车
    
    def __str__(self):
        return f"{self.user.username}的购物车-{self.shop.name}"
    
    @property
    def total_amount(self):
        """计算购物车总金额"""
        return sum(item.subtotal for item in self.items.all())
    
    @property
    def total_quantity(self):
        """计算购物车商品总数"""
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    """购物车项模型"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name="购物车")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="商品")
    quantity = models.PositiveIntegerField(default=1, verbose_name="数量")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="单价")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "购物车项"
        verbose_name_plural = verbose_name
        unique_together = ('cart', 'product')  # 一个购物车内同一个商品只能有一条记录
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def subtotal(self):
        """计算单项小计"""
        return self.quantity * self.price
