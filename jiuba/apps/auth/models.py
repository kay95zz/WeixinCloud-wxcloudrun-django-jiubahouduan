from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    wechat_openid = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    wechat_unionid = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    wechat_info = models.JSONField(default=dict)  # 存储微信用户信息
    created_from = models.CharField(max_length=20, default='website')  # 注册来源
    
    class Meta:
        db_table = 'auth_user'

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