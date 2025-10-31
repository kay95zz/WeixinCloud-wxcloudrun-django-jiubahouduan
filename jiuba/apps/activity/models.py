from django.db import models
from django.utils import timezone
from apps.shop.models import Shop  # 假设 Shop 模型在 apps/shop/models.py

class Activity(models.Model):
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        verbose_name="所属店铺",
        related_name="activities"
    )
    title = models.CharField("活动标题", max_length=200)
    description = models.TextField("活动描述", blank=True)

    # 👇 新增图片字段
    image = models.ImageField(
        "活动封面图",
        upload_to='activities/',  # 图片将保存在 MEDIA_ROOT/activities/ 目录下
        blank=True,
        null=True,
        help_text="建议尺寸：800x600，支持 JPG/PNG"
    )

    is_featured = models.BooleanField(
        "是否在总活动页展示",
        default=False,
        help_text="勾选后，该活动将出现在小程序首页的「总活动列表」中"
    )

    start_time = models.DateTimeField("开始时间")
    end_time = models.DateTimeField("结束时间")
    max_participants = models.PositiveIntegerField(
        "最大参与人数",
        null=True,
        blank=True,
        help_text="留空表示不限人数"
    )
    is_active = models.BooleanField("是否启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "活动"
        verbose_name_plural = "活动"
        ordering = ['start_time']

    def __str__(self):
        return f"{self.title} @ {self.shop.name}"

    def can_reserve(self):
        """判断当前是否还能预约（活动未开始）"""
        return self.start_time > timezone.now()

    def remaining_slots(self):
        """返回剩余名额（仅当设置了 max_participants 时有效）"""
        if self.max_participants is None:
            return float('inf')  # 无限
        from apps.reservation.models import Reservation
        confirmed_count = Reservation.objects.filter(
            activity=self,
            status__in=['confirmed', 'paid']
        ).count()
        return max(0, self.max_participants - confirmed_count)