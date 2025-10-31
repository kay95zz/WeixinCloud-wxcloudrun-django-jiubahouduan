from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from apps.shop.models import Shop

class User(AbstractUser):
    
    shop = models.ForeignKey(
        'shop.Shop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'is_active': True},
        verbose_name="所属店铺",
        help_text="仅员工需要填写"
    )

    """自定义用户模型"""
    phone = models.CharField(max_length=20, blank=True, verbose_name="手机号")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="余额")
    points = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="积分")
    avatar = models.ImageField(upload_to='avatars/%Y/%m/%d/', blank=True, verbose_name="头像")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "用户"
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return self.username