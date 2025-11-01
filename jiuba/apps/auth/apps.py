# apps/user_auth/apps.py
from django.apps import AppConfig

class UserAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.auth'  # 修改这里
    label = 'auth'      # 添加唯一标签
    verbose_name = '用户认证'