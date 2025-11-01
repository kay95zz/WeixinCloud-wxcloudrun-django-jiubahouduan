from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.utils import timezone
from datetime import date
from django.db.models import Sum, Count, Q
from apps.product.models import Product, Category
from apps.order.models import Order
from apps.shop.models import Shop
from apps.user.models import User
from apps.activity.models import Activity
from apps.notice.models import Notice
from django.http import HttpResponse
import csv
import xlwt
from apps.reservations.models import Reservation

def is_merchant(user):
    """检查用户是否为商家"""
    return user.is_authenticated and user.is_staff  # 临时使用 is_staff

class MerchantRequiredMixin:
    """商家权限Mixin"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/merchant/login/?next=' + request.path)
        
        if not request.user.is_staff:  # 直接使用 is_staff
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("您没有权限访问商家后台")
        
        return super().dispatch(request, *args, **kwargs)

# 登录视图
class MerchantLoginView(View):
    template_name = 'merchant/login.html'
    
    def get(self, request):
        if request.user.is_authenticated and is_merchant(request.user):
            next_url = request.GET.get('next', '/merchant/')
            return redirect(next_url)
        
        form = AuthenticationForm()
        next_url = request.GET.get('next', '')
        return render(request, self.template_name, {'form': form, 'next': next_url})
    
    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        next_url = request.POST.get('next', '/merchant/')
        
        if form.is_valid():
            user = form.get_user()
            if is_merchant(user):
                login(request, user)
                return redirect(next_url)
            else:
                form.add_error(None, '您没有商家后台访问权限')
        return render(request, self.template_name, {'form': form, 'next': next_url})

def merchant_logout(request):
    """商家后台退出视图"""
    logout(request)
    return redirect('merchant:login')

# 仪表板视图 - 修改为类视图
class MerchantDashboardView(MerchantRequiredMixin, View):
    def get(self, request):
        context = {
            'products_count': Product.objects.count(),
            'today_orders': Order.objects.filter(created_at__date=date.today()).count(),
            'users_count': User.objects.count(),
        }
        return render(request, 'merchant/dashboard.html', context)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取所有店铺的订单统计
        today = timezone.now().date()
        
        # 今日订单统计
        today_orders = Order.objects.filter(
            is_paid=True,
            created_at__date=today
        )
        
        # 总订单统计
        total_orders = Order.objects.filter(is_paid=True)
        
        # 计算统计信息
        today_stats = today_orders.aggregate(
            count=Count('id'),
            total_amount=Sum('total_amount'),
            total_points=Sum('total_points')
        )
        
        total_stats = total_orders.aggregate(
            count=Count('id'),
            total_amount=Sum('total_amount'),
            total_points=Sum('total_points')
        )
        
        # 获取最近订单
        recent_orders = Order.objects.filter(is_paid=True).select_related('user', 'shop').order_by('-created_at')[:10]
        
        context.update({
            'today_orders_count': today_stats['count'] or 0,
            'today_total_amount': today_stats['total_amount'] or 0,
            'today_total_points': today_stats['total_points'] or 0,
            'total_orders_count': total_stats['count'] or 0,
            'total_amount': total_stats['total_amount'] or 0,
            'total_points': total_stats['total_points'] or 0,
            'recent_orders': recent_orders,
        })
        
        return context

# 用户管理视图
class UserListView(MerchantRequiredMixin, ListView):
    model = User
    template_name = 'merchant/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        
        # 搜索功能
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        return queryset

class UserDetailView(MerchantRequiredMixin, View):
    template_name = 'merchant/user_detail.html'
    
    def get(self, request, pk):
        user = User.objects.get(pk=pk)
        return render(request, self.template_name, {'user': user})

class UserBalancePointsUpdateView(MerchantRequiredMixin, View):
    template_name = 'merchant/user_balance_points_form.html'
    
    def get(self, request, pk):
        user = User.objects.get(pk=pk)
        return render(request, self.template_name, {'user': user})
    
    def post(self, request, pk):
        user = User.objects.get(pk=pk)
        
        # 获取表单数据
        balance = request.POST.get('balance')
        points = request.POST.get('points')
        
        try:
            # 更新余额和积分
            if balance:
                user.balance = float(balance)
            if points:
                user.points = int(points)
            
            user.save()
            
            return redirect('merchant:user_detail', pk=user.pk)
            
        except (ValueError, TypeError):
            # 处理格式错误
            error_message = "余额或积分格式错误"
            return render(request, self.template_name, {
                'user': user,
                'error_message': error_message
            })


# 商品管理视图 - 添加 MerchantRequiredMixin
class ProductListView(MerchantRequiredMixin, ListView):
    model = Product
    template_name = 'merchant/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Product.objects.all().order_by('-created_at')
        
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        shop_filter = self.request.GET.get('shop')
        if shop_filter:
            queryset = queryset.filter(shop_id=shop_filter)
        
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        category_filter = self.request.GET.get('category')
        if category_filter:
            queryset = queryset.filter(category_id=category_filter)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['shops'] = Shop.objects.all()
        context['categories'] = Category.objects.filter(is_active=True)
        context['status_choices'] = Product.STATUS_CHOICES
        return context

# 其他视图类添加 MerchantRequiredMixin
class ProductCreateView(MerchantRequiredMixin, CreateView):
    model = Product
    template_name = 'merchant/product_form.html'
    fields = ['name', 'description', 'price', 'original_price', 'points_price', 'original_points_price', 'stock_quantity', 
              'category', 'shop', 'image', 'status', 'sort_order', 'is_available']
    success_url = reverse_lazy('merchant:product_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['shop'].queryset = Shop.objects.all()
        form.fields['category'].queryset = Category.objects.filter(is_active=True)
        return form

class ProductUpdateView(MerchantRequiredMixin, UpdateView):
    model = Product
    template_name = 'merchant/product_form.html'
    fields = ['name', 'description', 'price', 'original_price', 'points_price', 'original_points_price', 'stock_quantity', 
              'category', 'shop', 'image', 'status', 'sort_order', 'is_available']
    success_url = reverse_lazy('merchant:product_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['shop'].queryset = Shop.objects.all()
        form.fields['category'].queryset = Category.objects.filter(is_active=True)
        return form

class ProductDeleteView(MerchantRequiredMixin, DeleteView):
    model = Product
    template_name = 'merchant/product_confirm_delete.html'
    success_url = reverse_lazy('merchant:product_list')

# 订单视图
class MerchantOrderListView(MerchantRequiredMixin, ListView):
    """商家订单列表视图 - 支持导出和统计"""
    model = Order
    template_name = 'merchant/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_queryset(self):
        """获取所有店铺的订单（商家可以看到所有店铺）"""
        # 商家用户可以看到所有已支付订单
        queryset = Order.objects.filter(is_paid=True).select_related('user', 'shop')
        
        # 店铺筛选
        shop_filter = self.request.GET.get('shop')
        if shop_filter:
            queryset = queryset.filter(shop_id=shop_filter)
        
        # 支付方式过滤
        payment_method = self.request.GET.get('payment_method')
        if payment_method in ['cash', 'points']:
            queryset = queryset.filter(payment_method=payment_method)
        
        # 时间范围过滤
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # 搜索
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(user__username__icontains=search) |
                Q(customer_notes__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        
        # 获取所有店铺用于筛选
        shops = Shop.objects.filter(is_active=True)
        
        # 计算统计信息
        stats = queryset.aggregate(
            total_orders=Count('id'),
            total_cash_amount=Sum('total_amount'),
            total_points_amount=Sum('total_points'),
            cash_orders=Count('id', filter=Q(payment_method='cash')),
            points_orders=Count('id', filter=Q(payment_method='points'))
        )
        
        context.update({
            'total_orders': stats['total_orders'] or 0,
            'total_cash_amount': stats['total_cash_amount'] or 0,
            'total_points_amount': stats['total_points_amount'] or 0,
            'cash_orders': stats['cash_orders'] or 0,
            'points_orders': stats['points_orders'] or 0,
            'shops': shops,  # 添加店铺列表到上下文
            'current_filters': self.request.GET.dict(),
        })
        
        return context
    
    def render_to_response(self, context, **response_kwargs):
        """支持导出功能"""
        export_format = self.request.GET.get('export')
        
        if export_format == 'csv':
            return self.export_orders_csv(context['orders'])
        elif export_format == 'excel':
            return self.export_orders_excel(context['orders'])
        
        return super().render_to_response(context, **response_kwargs)
    
    def export_orders_csv(self, orders):
        """导出订单为CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="orders_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            '订单号', '用户', '店铺', '支付方式', '现金金额', '积分金额', 
            '商品数量', '顾客备注', '创建时间', '支付时间'
        ])
        
        for order in orders:
            writer.writerow([
                order.order_number,
                order.user.username,
                order.shop.name,
                order.get_payment_method_display(),
                float(order.total_amount),
                order.total_points,
                order.item_count,
                order.customer_notes,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.paid_at.strftime('%Y-%m-%d %H:%M:%S') if order.paid_at else ''
            ])
        
        return response
    
    def export_orders_excel(self, orders):
        """导出订单为Excel"""
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = f'attachment; filename="orders_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('订单列表')
        
        # 设置表头样式
        header_style = xlwt.XFStyle()
        header_font = xlwt.Font()
        header_font.bold = True
        header_style.font = header_font
        
        # 写入表头
        headers = ['订单号', '用户', '店铺', '支付方式', '现金金额', '积分金额', '商品数量', '顾客备注', '创建时间', '支付时间']
        for col, header in enumerate(headers):
            ws.write(0, col, header, header_style)
        
        # 写入数据
        for row, order in enumerate(orders, 1):
            ws.write(row, 0, order.order_number)
            ws.write(row, 1, order.user.username)
            ws.write(row, 2, order.shop.name)
            ws.write(row, 3, order.get_payment_method_display())
            ws.write(row, 4, float(order.total_amount))
            ws.write(row, 5, order.total_points)
            ws.write(row, 6, order.item_count)
            ws.write(row, 7, order.customer_notes)
            ws.write(row, 8, order.created_at.strftime('%Y-%m-%d %H:%M:%S'))
            ws.write(row, 9, order.paid_at.strftime('%Y-%m-%d %H:%M:%S') if order.paid_at else '')
        
        wb.save(response)
        return response
    
# 活动管理视图
class ActivityListView(MerchantRequiredMixin, ListView):
    model = Activity
    template_name = 'merchant/activity_list.html'
    context_object_name = 'activities'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Activity.objects.all().select_related('shop').order_by('-created_at')
        
        # 搜索功能
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        # 店铺筛选
        shop_filter = self.request.GET.get('shop')
        if shop_filter:
            queryset = queryset.filter(shop_id=shop_filter)
        
        # 状态筛选
        status_filter = self.request.GET.get('status')
        if status_filter:
            if status_filter == 'active':
                queryset = queryset.filter(is_active=True)
            elif status_filter == 'inactive':
                queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['shops'] = Shop.objects.all()
        return context

class ActivityCreateView(MerchantRequiredMixin, CreateView):
    model = Activity
    template_name = 'merchant/activity_form.html'
    fields = ['shop', 'title', 'description', 'image', 'start_time', 'end_time', 
              'max_participants', 'is_featured', 'is_active']
    success_url = reverse_lazy('merchant:activity_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # 设置店铺选择
        form.fields['shop'].queryset = Shop.objects.all()
        # 设置时间输入格式
        form.fields['start_time'].widget.attrs.update({'type': 'datetime-local'})
        form.fields['end_time'].widget.attrs.update({'type': 'datetime-local'})
        return form

class ActivityUpdateView(MerchantRequiredMixin, UpdateView):
    model = Activity
    template_name = 'merchant/activity_form.html'
    fields = ['shop', 'title', 'description', 'image', 'start_time', 'end_time', 
              'max_participants', 'is_featured', 'is_active']
    success_url = reverse_lazy('merchant:activity_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['shop'].queryset = Shop.objects.all()
        form.fields['start_time'].widget.attrs.update({'type': 'datetime-local'})
        form.fields['end_time'].widget.attrs.update({'type': 'datetime-local'})
        return form

class ActivityDeleteView(MerchantRequiredMixin, DeleteView):
    model = Activity
    template_name = 'merchant/activity_confirm_delete.html'
    success_url = reverse_lazy('merchant:activity_list')

class ActivityDetailView(MerchantRequiredMixin, View):
    template_name = 'merchant/activity_detail.html'
    
    def get(self, request, pk):
        activity = Activity.objects.select_related('shop').get(pk=pk)
        return render(request, self.template_name, {'activity': activity})
    
class MerchantReservationListView(MerchantRequiredMixin, ListView):
    """商家预约列表视图 - 可以看到所有预约"""
    model = Reservation
    template_name = 'merchant/reservation_list.html'
    context_object_name = 'reservations'
    paginate_by = 20
    
    def get_queryset(self):
        """获取所有预约记录"""
        # print("=== 开始获取预约数据 ===")
        
        # 获取所有预约
        queryset = Reservation.objects.all().select_related('user', 'activity', 'shop')
        # print(f"初始查询集数量: {queryset.count()}")
        
        # 店铺筛选
        shop_filter = self.request.GET.get('shop')
        if shop_filter:
            queryset = queryset.filter(shop_id=shop_filter)
            # print(f"店铺过滤后数量: {queryset.count()}")
        
        # 状态筛选
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            # print(f"状态过滤后数量: {queryset.count()}")
        
        # 活动筛选
        activity_filter = self.request.GET.get('activity')
        if activity_filter:
            queryset = queryset.filter(activity_id=activity_filter)
            # print(f"活动过滤后数量: {queryset.count()}")
        
        # 时间范围筛选
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
            # print(f"开始日期过滤后数量: {queryset.count()}")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
            # print(f"结束日期过滤后数量: {queryset.count()}")
        
        # 搜索
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(contact_phone__icontains=search) |
                Q(activity__title__icontains=search) |
                Q(shop__name__icontains=search)
            )
            # print(f"搜索过滤后数量: {queryset.count()}")
        
        final_count = queryset.count()
        # print(f"最终查询集数量: {final_count}")
        # print("=== 结束获取预约数据 ===")
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取所有店铺用于筛选
        shops = Shop.objects.filter(is_active=True)
        
        # 获取所有活动用于筛选
        activities = Activity.objects.filter(is_active=True)
        
        # 获取统计信息
        queryset = self.get_queryset()
        stats = queryset.aggregate(
            total=Count('id'),
            confirmed=Count('id', filter=Q(status='confirmed')),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled'))
        )
        
        context.update({
            'total_reservations': stats['total'] or 0,
            'confirmed_reservations': stats['confirmed'] or 0,
            'completed_reservations': stats['completed'] or 0,
            'cancelled_reservations': stats['cancelled'] or 0,
            'shops': shops,  # 添加店铺列表
            'activities': activities,  # 添加活动列表
            'current_filters': self.request.GET.dict(),
        })
        
        return context

class MerchantActivityReservationView(MerchantRequiredMixin, DetailView):
    """商家活动预约详情视图 - 可以看到所有活动的预约"""
    model = Activity
    template_name = 'merchant/activity_reservations.html'
    context_object_name = 'activity'
    
    def get_queryset(self):
        """可以查看所有活动"""
        return Activity.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activity = self.get_object()
        
        # 获取该活动的所有预约
        reservations = Reservation.objects.filter(
            activity=activity
        ).select_related('user', 'shop').order_by('-created_at')
        
        # 统计信息
        stats = reservations.aggregate(
            total=Count('id'),
            confirmed=Count('id', filter=Q(status='confirmed')),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled'))
        )
        
        context.update({
            'reservations': reservations,
            'total_reservations': stats['total'] or 0,
            'confirmed_reservations': stats['confirmed'] or 0,
            'completed_reservations': stats['completed'] or 0,
            'cancelled_reservations': stats['cancelled'] or 0,
            'remaining_slots': activity.remaining_slots(),
        })
        
        return context
    
class CompleteReservationView(MerchantRequiredMixin, View):
    """完成预约"""
    def post(self, request, reservation_id):
        reservation = get_object_or_404(Reservation, id=reservation_id)
        
        # 检查权限：只能操作自己店铺的预约
        if not hasattr(request.user, 'shop') or reservation.shop != request.user.shop:
            messages.error(request, "无权操作此预约")
            return redirect('merchant:reservation_list')
        
        if reservation.status != 'confirmed':
            messages.error(request, "只有已确认的预约才能完成")
            return redirect('merchant:reservation_list')
        
        reservation.status = 'completed'
        reservation.save()
        
        messages.success(request, f"预约 #{reservation.id} 已完成")
        return redirect('merchant:reservation_list')
    
# 店铺管理视图
class ShopListView(MerchantRequiredMixin, ListView):
    model = Shop
    template_name = 'merchant/shop_list.html'
    context_object_name = 'shops'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Shop.objects.all().order_by('-created_at')
        
        # 搜索功能
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(address__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
        
        # 状态筛选
        status_filter = self.request.GET.get('status')
        if status_filter:
            if status_filter == 'active':
                queryset = queryset.filter(is_active=True)
            elif status_filter == 'inactive':
                queryset = queryset.filter(is_active=False)
        
        return queryset

class ShopUpdateView(MerchantRequiredMixin, UpdateView):
    model = Shop
    template_name = 'merchant/shop_form.html'
    fields = ['name', 'address', 'phone', 'description', 'logo', 'is_active']
    success_url = reverse_lazy('merchant:shop_list')

class ShopDetailView(MerchantRequiredMixin, View):
    template_name = 'merchant/shop_detail.html'
    
    def get(self, request, pk):
        shop = Shop.objects.get(pk=pk)
        return render(request, self.template_name, {'shop': shop})
    
# 公告管理视图
class NoticeListView(MerchantRequiredMixin, ListView):
    model = Notice
    template_name = 'merchant/notice_list.html'
    context_object_name = 'notices'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Notice.objects.all().select_related('shop').order_by('-created_at')
        
        # 搜索功能
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query)
            )
        
        # 店铺筛选
        shop_filter = self.request.GET.get('shop')
        if shop_filter:
            queryset = queryset.filter(shop_id=shop_filter)
        
        # 状态筛选
        status_filter = self.request.GET.get('status')
        if status_filter:
            if status_filter == 'active':
                queryset = queryset.filter(is_active=True)
            elif status_filter == 'inactive':
                queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['shops'] = Shop.objects.all()
        return context

class NoticeCreateView(MerchantRequiredMixin, CreateView):
    model = Notice
    template_name = 'merchant/notice_form.html'
    fields = ['shop', 'title', 'content', 'is_active']
    success_url = reverse_lazy('merchant:notice_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # 设置店铺选择
        form.fields['shop'].queryset = Shop.objects.all()
        return form

class NoticeUpdateView(MerchantRequiredMixin, UpdateView):
    model = Notice
    template_name = 'merchant/notice_form.html'
    fields = ['shop', 'title', 'content', 'is_active']
    success_url = reverse_lazy('merchant:notice_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['shop'].queryset = Shop.objects.all()
        return form

class NoticeDeleteView(MerchantRequiredMixin, DeleteView):
    model = Notice
    template_name = 'merchant/notice_confirm_delete.html'
    success_url = reverse_lazy('merchant:notice_list')

class NoticeDetailView(MerchantRequiredMixin, View):
    template_name = 'merchant/notice_detail.html'
    
    def get(self, request, pk):
        notice = Notice.objects.select_related('shop').get(pk=pk)
        return render(request, self.template_name, {'notice': notice})