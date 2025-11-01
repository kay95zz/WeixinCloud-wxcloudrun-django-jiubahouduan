from django.db import models
from django.utils import timezone
from apps.shop.models import Shop  # 导入 Shop 模型

class Category(models.Model):
    """商品分类"""
    name = models.CharField(max_length=100, verbose_name="分类名称")
    description = models.TextField(blank=True, verbose_name="分类描述")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "商品分类"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """商品模型"""
    STATUS_CHOICES = (
        ('draft', '草稿'),
        ('published', '已上架'),
        ('out_of_stock', '缺货'),
        ('discontinued', '已下架'),
    )
    
    name = models.CharField(max_length=100, verbose_name="商品名称")
    description = models.TextField(blank=True, verbose_name="商品描述")
    
    # 现金价格
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="现金价格")
    original_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="现金原价"
    )
    
    # 🆕 积分价格
    points_price = models.IntegerField(
        default=0, 
        verbose_name="积分价格",
        help_text="购买此商品所需的积分数量，0表示不支持积分购买"
    )
    original_points_price = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        verbose_name="积分原价",
        help_text="积分原价，用于显示折扣"
    )
    
    image = models.ImageField(upload_to='products/%Y/%m/%d/', verbose_name="商品图片")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, verbose_name="商品分类"
    )
    shop = models.ForeignKey(
        Shop, on_delete=models.CASCADE, related_name='products', verbose_name="所属店铺"
    )
    is_available = models.BooleanField(default=True, verbose_name="是否可用")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="状态"
    )
    stock_quantity = models.IntegerField(default=0, verbose_name="库存数量")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "商品"
        verbose_name_plural = verbose_name
        ordering = ['sort_order', '-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.shop.name}"
    
    @property
    def is_on_sale(self):
        """检查商品是否有现金折扣"""
        return self.original_price and self.original_price > self.price
    
    @property
    def is_points_on_sale(self):
        """检查商品是否有积分折扣"""
        return (self.original_points_price and 
                self.original_points_price > self.points_price > 0)
    
    @property
    def can_buy_with_points(self):
        """检查是否支持积分购买"""
        return self.points_price > 0