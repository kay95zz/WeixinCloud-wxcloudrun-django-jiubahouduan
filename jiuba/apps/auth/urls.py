from django.urls import path
from . import views

urlpatterns = [
    path('wechat/auth_url/', views.WeChatAuthURLView.as_view(), name='wechat-auth-url'),
    path('wechat/callback/', views.WeChatCallbackView.as_view(), name='wechat-callback'),
    path('wechat/bind/', views.WeChatBindView.as_view(), name='wechat-bind'),
]