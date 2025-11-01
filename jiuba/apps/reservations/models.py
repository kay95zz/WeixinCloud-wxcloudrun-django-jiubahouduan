# apps/reservation/models.py

from django.db import models
from apps.user.models import User
from apps.activity.models import Activity
from apps.shop.models import Shop

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('confirmed', '已确认'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, verbose_name="预约活动")
    shop = models.ForeignKey('shop.Shop', on_delete=models.CASCADE, verbose_name="店铺")
    contact_phone = models.CharField("联系电话", max_length=20)
    note = models.TextField("备注", blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "预约记录"
        verbose_name_plural = "预约记录"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} 预约 {self.activity.title}"

    def save(self, *args, **kwargs):
        if not self.shop_id:
            self.shop = self.activity.shop
        super().save(*args, **kwargs)