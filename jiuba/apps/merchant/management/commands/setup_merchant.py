from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.product.models import Product
from apps.order.models import Order

class Command(BaseCommand):
    def handle(self, *args, **options):
        # 创建商家用户组
        merchant_group, created = Group.objects.get_or_create(name='merchant')
        
        # 分配商品和订单的权限
        product_permissions = Permission.objects.filter(
            content_type__model='product'
        )
        order_permissions = Permission.objects.filter(
            content_type__model='order'
        )
        
        merchant_group.permissions.set(list(product_permissions) + list(order_permissions))
        self.stdout.write(self.style.SUCCESS('商家用户组创建完成'))