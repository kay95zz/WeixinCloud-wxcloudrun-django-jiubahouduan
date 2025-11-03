# user/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import login, logout
from django.db import transaction
import random
import string
from .models import User
from .serializers import UserSerializer, UserRegistrationSerializer, UserLoginSerializer, UserBalancePointsSerializer
from .permissions import IsAdminUser

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action in ['register', 'login', 'wechat_smart_login']:
            return [AllowAny()]
        elif self.action in ['update_balance_points', 'user_list']:
            return [IsAuthenticated(), IsAdminUser]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """用户注册"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': '注册成功',
                'user_id': user.id,
                'username': user.username
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """用户登录"""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            return Response({
                'message': '登录成功',
                'session_id': request.session.session_key,
                'user_id': user.id,
                'username': user.username
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def wechat_smart_login(self, request):
        """
        微信智能登录
        使用手机号和OpenID混合识别方案
        """
        phone = request.data.get('phone')
        openid = request.data.get('openid')
        user_info = request.data.get('user_info', {})
        
        # 参数验证
        if not openid and not phone:
            return Response(
                {'error': '需要提供手机号或OpenID'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            user = None
            is_new_user = False
            
            # 方案1: 优先使用手机号识别
            if phone:
                try:
                    user = User.objects.select_for_update().get(phone=phone)
                    # 如果找到用户，绑定微信OpenID（如果还没有）
                    if openid and not user.wechat_openid:
                        user.wechat_openid = openid
                        user.save()
                except User.DoesNotExist:
                    # 手机号不存在，继续尝试OpenID
                    pass
            
            # 方案2: 使用OpenID识别
            if not user and openid:
                try:
                    user = User.objects.select_for_update().get(wechat_openid=openid)
                except User.DoesNotExist:
                    # OpenID也不存在，需要创建新用户
                    pass
            
            # 方案3: 创建新用户
            if not user:
                username = self._generate_username(
                    user_info.get('nickname'), 
                    phone
                )
                user = User.objects.create(
                    username=username,
                    phone=phone or '',
                    wechat_openid=openid,
                    email=user_info.get('email', ''),
                )
                
                # 设置微信头像（如果提供）
                if user_info.get('avatar'):
                    # 这里可以添加下载并保存头像的逻辑
                    pass
                    
                is_new_user = True
            
            # 登录用户
            login(request, user)
            
            return Response({
                'message': '登录成功',
                'user_id': user.id,
                'username': user.username,
                'is_new_user': is_new_user,
                'has_phone': bool(user.phone),
                'has_wechat_bind': bool(user.wechat_openid)
            })
    
    def _generate_username(self, nickname, phone):
        """生成唯一用户名"""
        # 使用昵称或手机号作为基础
        base = nickname or f"user{phone[-4:]}" if phone else "user"
        
        # 清理特殊字符
        import re
        base = re.sub(r'[^\w\s-]', '', base).strip()
        base = base or "user"
        
        username = base
        counter = 1
        
        # 确保用户名唯一
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
            if counter > 100:
                # 防止无限循环，添加随机后缀
                random_suffix = ''.join(random.choices(string.digits, k=4))
                username = f"{base}{random_suffix}"
                break
                
        return username
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """用户登出"""
        logout(request)
        return Response({'message': '登出成功'})
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """获取当前用户信息"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def user_list(self, request):
        """
        获取用户列表（商家和管理员专用）
        用于在后台选择用户修改积分和余额
        """
        queryset = User.objects.all().order_by('-date_joined')
        
        # 搜索功能
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                username__icontains=search
            ) | queryset.filter(
                phone__icontains=search
            ) | queryset.filter(
                email__icontains=search
            )
        
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def update_balance_points(self, request, pk=None):
        """
        修改用户余额和积分（商家和管理员专用）
        """
        user = self.get_object()
        serializer = UserBalancePointsSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            # 记录修改日志
            old_balance = user.balance
            old_points = user.points
            new_balance = serializer.validated_data.get('balance', old_balance)
            new_points = serializer.validated_data.get('points', old_points)
            
            serializer.save()
            
            return Response({
                'message': '修改成功',
                'user_id': user.id,
                'username': user.username,
                'old_balance': float(old_balance),
                'new_balance': float(new_balance),
                'old_points': float(old_points),
                'new_points': float(new_points),
                'balance_change': float(new_balance - old_balance),
                'points_change': float(new_points - old_points)
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_balance(self, request, pk=None):
        """
        增加用户余额（商家和管理员专用）
        """
        user = self.get_object()
        amount = request.data.get('amount', 0)
        
        try:
            amount = float(amount)
            if amount <= 0:
                return Response(
                    {'error': '金额必须大于0'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': '金额格式错误'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_balance = user.balance
        user.balance += amount
        user.save()
        
        return Response({
            'message': '余额增加成功',
            'user_id': user.id,
            'username': user.username,
            'amount': amount,
            'old_balance': float(old_balance),
            'new_balance': float(user.balance)
        })
    
    @action(detail=True, methods=['post'])
    def add_points(self, request, pk=None):
        """
        增加用户积分（商家和管理员专用）
        """
        user = self.get_object()
        points = request.data.get('points', 0)
        
        try:
            points = int(points)
            if points <= 0:
                return Response(
                    {'error': '积分必须大于0'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': '积分格式错误'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_points = user.points
        user.points += points
        user.save()
        
        return Response({
            'message': '积分增加成功',
            'user_id': user.id,
            'username': user.username,
            'points': points,
            'old_points': old_points,
            'new_points': user.points
        })