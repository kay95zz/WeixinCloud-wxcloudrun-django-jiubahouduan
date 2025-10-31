from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import login, logout
from .models import User
from .serializers import UserSerializer, UserRegistrationSerializer, UserLoginSerializer, UserBalancePointsSerializer
from .permissions import IsMerchantUser, IsAdminUser

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action in ['register', 'login']:
            return [AllowAny()]
        elif self.action in ['update_balance_points', 'user_list']:
            return [IsAuthenticated(), IsAdminUser]  # 直接用 IsAdminUser
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