from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Reservation
from .serializers import ReservationSerializer, ReservationCreateSerializer

class ReservationViewSet(viewsets.ModelViewSet):
    """
    预约视图集
    - 客户可以创建、查看、取消自己的预约
    - 店铺员工/店主可以完成预约
    """
    queryset = Reservation.objects.all()
    permission_classes = [IsAuthenticated]  # 默认需要登录
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'create':
            return ReservationCreateSerializer
        return ReservationSerializer

    def get_queryset(self):
        """根据用户权限返回对应的查询集"""
        user = self.request.user
        
        # 普通用户只能看到自己的预约
        if not user.is_staff:
            return Reservation.objects.filter(user=user)
        
        # 管理员可以看到所有预约
        if user.is_superuser:
            return Reservation.objects.all()
        
        # 员工用户可以看到自己店铺的预约（需要根据您的业务逻辑调整）
        # 这里假设员工通过其他方式关联到店铺
        return Reservation.objects.all()

    def get_permissions(self):
        """根据动作动态设置权限"""
        if self.action in ['complete', 'shop_reservations']:
            # 完成预约和查看店铺预约需要员工权限
            return [IsAuthenticated()]  # 可以根据需要改为 [IsAdminUser()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """创建预约"""
        return super().create(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """获取预约列表"""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """获取预约详情"""
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['patch'])
    def cancel(self, request, pk=None):
        """取消预约"""
        reservation = self.get_object()
        
        # 检查权限：用户只能取消自己的预约
        if reservation.user != request.user and not request.user.is_staff:
            return Response(
                {"error": "无权取消此预约"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if reservation.status != 'confirmed':
            return Response(
                {"error": "只有已确认的预约才能取消"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reservation.status = 'cancelled'
        reservation.save()
        
        serializer = self.get_serializer(reservation)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def complete(self, request, pk=None):
        """完成预约（店铺端）"""
        reservation = self.get_object()
        
        # 检查权限：只有员工可以完成预约
        if not request.user.is_staff:
            return Response(
                {"error": "无权完成预约"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if reservation.status != 'confirmed':
            return Response(
                {"error": "只有已确认的预约才能完成"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reservation.status = 'completed'
        reservation.save()
        
        serializer = self.get_serializer(reservation)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_reservations(self, request):
        """获取当前用户的预约列表（客户端）"""
        queryset = self.get_queryset().filter(user=request.user)
        
        # 支持分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def shop_reservations(self, request):
        """获取当前店铺相关的预约列表（店铺端）"""
        # 检查权限：只有员工可以查看店铺预约
        if not request.user.is_staff:
            return Response(
                {"error": "无权查看店铺预约"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        
        # 支持状态过滤
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 支持分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)