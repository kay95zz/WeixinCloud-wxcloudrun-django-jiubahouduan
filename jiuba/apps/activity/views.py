from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q
from .models import Activity
from .serializers import ActivitySerializer

class ActivityViewSet(viewsets.ModelViewSet):
    """
    活动管理 ViewSet
    """
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['start_time', 'end_time', 'created_at', 'price']
    ordering = ['start_time']
    
    def get_permissions(self):
        """
        权限控制：
        - 列表、详情、搜索：所有用户可访问
        - 创建、更新、删除：需要管理员权限
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'toggle_status', 'toggle_featured']:
            permission_classes = [IsAuthenticated, IsAdminUser]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        根据用户权限返回不同的查询集
        - 管理员：可以看到所有活动
        - 普通用户：只能看到活跃且未结束的活动
        """
        queryset = super().get_queryset().select_related('shop')
        
        # 管理员可以看到所有活动
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return queryset
        
        # 普通用户只能看到活跃且未结束的活动
        now = timezone.now()
        return queryset.filter(
            is_active=True,
            end_time__gt=now
        )
    
    def list(self, request, *args, **kwargs):
        """
        获取活动列表 - 默认返回所有可见活动
        可以通过查询参数进行过滤
        """
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        获取推荐特色活动
        """
        now = timezone.now()
        queryset = self.get_queryset().filter(
            is_active=True,
            is_featured=True,
            end_time__gt=now
        ).order_by('start_time')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def ongoing(self, request):
        """
        获取进行中的活动
        """
        now = timezone.now()
        queryset = self.get_queryset().filter(
            is_active=True,
            start_time__lte=now,
            end_time__gt=now
        ).order_by('start_time')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        获取即将开始的活动
        """
        now = timezone.now()
        queryset = self.get_queryset().filter(
            is_active=True,
            start_time__gt=now
        ).order_by('start_time')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """
        获取今日活动
        """
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timezone.timedelta(days=1)
        
        queryset = self.get_queryset().filter(
            is_active=True,
            start_time__gte=today_start,
            start_time__lt=today_end,
            end_time__gt=now
        ).order_by('start_time')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        活动搜索接口
        """
        queryset = self.get_queryset().filter(is_active=True)
        
        # 获取查询参数
        search_term = request.query_params.get('q', None)
        shop_id = request.query_params.get('shop_id', None)
        date = request.query_params.get('date', None)
        activity_type = request.query_params.get('type', None)
        
        # 关键词搜索
        if search_term:
            queryset = queryset.filter(
                Q(title__icontains=search_term) | 
                Q(description__icontains=search_term)
            )
        
        # 按店铺筛选
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)
            
        # 按日期筛选
        if date:
            try:
                target_date = timezone.datetime.strptime(date, '%Y-%m-%d').date()
                queryset = queryset.filter(start_time__date=target_date)
            except ValueError:
                pass
        
        # 按活动类型筛选
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        # 只返回未结束的活动
        now = timezone.now()
        queryset = queryset.filter(end_time__gt=now).order_by('start_time')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def shop_activities(self, request, pk=None):
        """
        获取指定店铺的活动列表
        """
        shop_id = pk
        now = timezone.now()
        queryset = self.get_queryset().filter(
            shop_id=shop_id,
            is_active=True,
            end_time__gt=now
        ).order_by('start_time')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """
        切换活动激活状态（管理员功能）
        """
        activity = self.get_object()
        activity.is_active = not activity.is_active
        activity.save()
        
        message = f"活动{'已激活' if activity.is_active else '已停用'}"
        return Response({
            "message": message,
            "is_active": activity.is_active
        })
    
    @action(detail=True, methods=['post'])
    def toggle_featured(self, request, pk=None):
        """
        切换活动推荐状态（管理员功能）
        """
        activity = self.get_object()
        activity.is_featured = not activity.is_featured
        activity.save()
        
        message = f"活动{'已设为推荐' if activity.is_featured else '已取消推荐'}"
        return Response({
            "message": message,
            "is_featured": activity.is_featured
        })