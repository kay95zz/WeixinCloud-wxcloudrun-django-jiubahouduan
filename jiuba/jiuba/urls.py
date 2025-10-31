"""
URL configuration for jiuba project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.http import HttpResponseForbidden

def admin_required(view_func):
    """只有管理员才能访问Django Admin"""
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # 未登录，让Django处理重定向到登录页
            return view_func(request, *args, **kwargs)
        
        # 已登录，检查权限
        if request.user.is_staff and hasattr(request.user, 'user_type') and request.user.user_type == 'admin':
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden("您没有权限访问管理员后台")
    
    return _wrapped_view

# 应用权限控制
admin.site.login = admin_required(admin.site.login)

# 根路径欢迎页面
def home(request):
    """根路径欢迎页面"""
    return JsonResponse({
        'message': '🎉 酒霸后端 API 服务运行正常!',
        'status': 'success',
        'version': '1.0.0',
        'timestamp': '2025-11-01 03:50:00',
        'endpoints': {
            'admin': {
                'url': '/admin/',
                'description': 'Django 管理员后台'
            },
            'merchant': {
                'url': '/merchant/',
                'description': '商家管理接口'
            },
            'api': {
                'auth': {
                    'url': '/api/auth/',
                    'description': '用户认证接口'
                },
                'cart': {
                    'url': '/api/cart/',
                    'description': '购物车接口'
                },
                'shop': {
                    'url': '/api/shop/',
                    'description': '店铺接口'
                },
                'product': {
                    'url': '/api/product/',
                    'description': '商品接口'
                },
                'orders': {
                    'url': '/api/orders/',
                    'description': '订单接口'
                },
                'activity': {
                    'url': '/api/activity/',
                    'description': '活动接口'
                },
                'reservations': {
                    'url': '/api/reservations/',
                    'description': '预约接口'
                }
            }
        },
        'documentation': '请联系开发团队获取完整 API 文档',
        'health_check': '服务状态: ✅ 正常运行'
    })

urlpatterns = [
    path('', home, name='home'),  # 添加根路径欢迎页面
    path('admin/', admin.site.urls),
    path('merchant/', include('apps.merchant.urls')),  # 新增商家后台
    path('api/cart/', include('apps.cart.urls')),
    path('api/auth/', include('apps.user.urls')),
    path('api/shop/', include('apps.shop.urls')),
    path('api/product/', include('apps.product.urls')),
    path('api/orders/', include('apps.order.urls')),
    path('api/activity/', include('apps.activity.urls')),
    path('api/reservations/', include('apps.reservations.urls')),
]

# 开发环境下提供媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)