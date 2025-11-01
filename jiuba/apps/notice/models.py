from django.db import models
from django.utils import timezone
from apps.shop.models import Shop

class Notice(models.Model):
    """公告模型 - 简化版"""
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        verbose_name="所属店铺",
        related_name="notices"
    )
    
    title = models.CharField("公告标题", max_length=200)
    content = models.TextField("公告内容")
    
    is_active = models.BooleanField("是否启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    
    class Meta:
        verbose_name = "公告"
        verbose_name_plural = "公告"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.shop.name}"