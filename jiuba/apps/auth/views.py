from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login
from django.db import transaction
import random
import string

from .models import User, WechatAuth
from .wechat_service import WeChatService
from .serializers import WeChatCallbackSerializer, WeChatBindSerializer

class WeChatAuthURLView(APIView):
    """获取微信授权URL"""
    
    def get(self, request):
        redirect_uri = request.GET.get('redirect_uri')
        if not redirect_uri:
            return Response({"error": "缺少redirect_uri参数"}, status=status.HTTP_400_BAD_REQUEST)
        
        scope = request.GET.get('scope', 'snsapi_userinfo')
        state = request.GET.get('state', '')
        
        wechat_service = WeChatService()
        auth_url = wechat_service.get_auth_url(redirect_uri, scope, state)
        
        return Response({
            "auth_url": auth_url,
            "app_id": wechat_service.app_id
        })

class WeChatCallbackView(APIView):
    """微信授权回调处理"""
    
    def post(self, request):
        serializer = WeChatCallbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        wechat_service = WeChatService()
        
        # 1. 获取access_token和openid
        token_info = wechat_service.get_access_token(code)
        if 'errcode' in token_info and token_info['errcode'] != 0:
            return Response({
                "error": "微信授权失败",
                "detail": token_info.get('errmsg', '未知错误')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        openid = token_info['openid']
        access_token = token_info['access_token']
        refresh_token = token_info.get('refresh_token', '')
        expires_in = token_info.get('expires_in', 7200)
        
        with transaction.atomic():
            # 2. 检查用户是否已存在
            try:
                user = User.objects.select_for_update().get(wechat_openid=openid)
                is_new_user = False
                
                # 更新微信认证信息
                wechat_auth, created = WechatAuth.objects.get_or_create(
                    user=user,
                    openid=openid,
                    defaults={
                        'unionid': token_info.get('unionid'),
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'expires_in': expires_in
                    }
                )
                
                if not created:
                    wechat_auth.access_token = access_token
                    wechat_auth.refresh_token = refresh_token
                    wechat_auth.expires_in = expires_in
                    wechat_auth.save()
                    
            except User.DoesNotExist:
                # 3. 新用户：获取用户信息并创建账号
                user_info = wechat_service.get_user_info(access_token, openid)
                
                if 'errcode' in user_info and user_info['errcode'] != 0:
                    # 如果获取用户信息失败，创建基础用户
                    nickname = f"微信用户{openid[-8:]}"
                    user_info = {}
                else:
                    nickname = user_info.get('nickname', f"微信用户{openid[-8:]}")
                
                # 生成唯一用户名
                username = self._generate_unique_username(nickname)
                
                # 创建用户
                user = User.objects.create(
                    username=username,
                    wechat_openid=openid,
                    wechat_unionid=token_info.get('unionid'),
                    wechat_info=user_info,
                    created_from='wechat'
                )
                
                # 创建微信认证记录
                WechatAuth.objects.create(
                    user=user,
                    openid=openid,
                    unionid=token_info.get('unionid'),
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=expires_in
                )
                
                is_new_user = True
            
            # 4. 登录用户（使用你现有的认证系统）
            # 这里假设你使用Django的session认证，如果使用JWT需要相应调整
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "message": "登录成功",
                "user_id": user.id,
                "username": user.username,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "is_new_user": is_new_user,
                "nickname": user.wechat_info.get('nickname', '') if user.wechat_info else ''
            })
    
    def _generate_unique_username(self, nickname):
        """生成唯一的用户名"""
        # 清理昵称中的特殊字符
        base_username = ''.join(c for c in nickname if c.isalnum() or c in ['_', '-'])
        base_username = base_username or 'wechat_user'
        
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            random_suffix = ''.join(random.choices(string.digits, k=4))
            username = f"{base_username}_{random_suffix}"
            counter += 1
            if counter > 10:  # 防止无限循环
                username = f"wechat_user_{random_suffix}"
                break
            
        return username

class WeChatBindView(APIView):
    """绑定微信到现有账号"""
    
    def post(self, request):
        serializer = WeChatBindSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        code = serializer.validated_data['code']
        
        # 验证用户密码
        user = authenticate(username=username, password=password)
        if not user:
            return Response({
                "error": "用户名或密码错误"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取微信信息
        wechat_service = WeChatService()
        token_info = wechat_service.get_access_token(code)
        
        if 'errcode' in token_info and token_info['errcode'] != 0:
            return Response({
                "error": "微信授权失败",
                "detail": token_info.get('errmsg', '未知错误')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        openid = token_info['openid']
        
        # 检查微信是否已被绑定
        if User.objects.filter(wechat_openid=openid).exists():
            return Response({
                "error": "该微信账号已被绑定"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 绑定微信
        user.wechat_openid = openid
        user.wechat_unionid = token_info.get('unionid')
        user.save()
        
        # 创建微信认证记录
        WechatAuth.objects.create(
            user=user,
            openid=openid,
            unionid=token_info.get('unionid'),
            access_token=token_info.get('access_token'),
            refresh_token=token_info.get('refresh_token', ''),
            expires_in=token_info.get('expires_in', 7200)
        )
        
        return Response({
            "message": "绑定成功",
            "user_id": user.id,
            "username": user.username
        })