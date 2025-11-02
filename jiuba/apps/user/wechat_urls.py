# apps/user/wechat_urls.py
from django.urls import path
from .views import WeChatAuthURLView, WeChatCallbackView, WeChatBindView

urlpatterns = [
    path('auth_url/', WeChatAuthURLView.as_view(), name='wechat-auth-url'),
    path('callback/', WeChatCallbackView.as_view(), name='wechat-callback'),
    path('bind/', WeChatBindView.as_view(), name='wechat-bind'),
]