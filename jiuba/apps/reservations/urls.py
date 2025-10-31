# apps/reservation/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'', views.ReservationViewSet, basename='reservation')

urlpatterns = [
    # 包含路由器生成的所有 URL
    path('', include(router.urls)),
]