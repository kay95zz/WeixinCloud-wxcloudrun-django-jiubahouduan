import django_filters
from .models import Product

class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
    category = django_filters.NumberFilter(field_name='category_id')
    shop = django_filters.NumberFilter(field_name='shop_id')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')

    
    class Meta:
        model = Product
        fields = {
            'category_id': ['exact'],
            'shop_id': ['exact'],
            'status': ['exact'],
            'is_available': ['exact'],
            'name': ['icontains'],
            'description': ['icontains'],
        }

    def filter_in_stock(self, queryset, name, value):
        """自定义库存过滤方法"""
        if value:
            # in_stock=true: 库存大于0
            return queryset.filter(stock_quantity__gt=0)
        else:
            # in_stock=false: 库存等于0
            return queryset.filter(stock_quantity=0)