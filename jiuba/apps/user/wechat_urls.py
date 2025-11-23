from django.urls import path
from . import views

urlpatterns = [
    path('smart_login/', views.UserViewSet.as_view({'post': 'wechat_smart_login'}), name='wechat-smart-login'),
]