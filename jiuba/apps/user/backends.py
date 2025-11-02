from django.contrib.auth.backends import ModelBackend
from .models import User

# Backend
class WeChatBackend(ModelBackend):
    """微信登录认证后端"""
    
    def authenticate(self, request, openid=None, **kwargs):
        if openid is None:
            return None
            
        try:
            user = User.objects.get(wechat_openid=openid)
            return user
        except User.DoesNotExist:
            return None