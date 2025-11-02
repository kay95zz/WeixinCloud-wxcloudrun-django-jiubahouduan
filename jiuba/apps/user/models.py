from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from apps.shop.models import Shop

class User(AbstractUser):

    # 微信相关字段（从 auth/models.py 迁移过来）
    wechat_openid = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    wechat_unionid = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    wechat_info = models.JSONField(default=dict)  # 存储微信用户信息
    created_from = models.CharField(max_length=20, default='website')  # 注册来源
    
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
        db_table = 'auth_user'  # 保持与原来一致
    
    def __str__(self):
        return self.username
    
class WechatAuth(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wechat_auths')
    openid = models.CharField(max_length=64, db_index=True)
    unionid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    access_token = models.CharField(max_length=512, null=True, blank=True)
    refresh_token = models.CharField(max_length=512, null=True, blank=True)
    expires_in = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'wechat_auth'