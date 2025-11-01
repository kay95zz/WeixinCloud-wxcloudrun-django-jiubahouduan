from django.apps import AppConfig

class NoticeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notice'
    verbose_name = '公告管理'