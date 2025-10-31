from django.db import models
from django.utils import timezone

class Shop(models.Model):
    """店铺模型"""
    name = models.CharField(max_length=100, verbose_name="店铺名称")
    address = models.CharField(max_length=200, verbose_name="地址", blank=True)
    phone = models.CharField(max_length=20, verbose_name="联系电话", blank=True)
    description = models.TextField(blank=True, verbose_name="店铺描述")
    logo = models.ImageField(upload_to='shop_logos/%Y/%m/%d/', verbose_name="店铺Logo", blank=True)
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "店铺"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def active_products_count(self):
        """获取该店铺的活跃商品数量"""
        return self.products.filter(is_available=True).count()