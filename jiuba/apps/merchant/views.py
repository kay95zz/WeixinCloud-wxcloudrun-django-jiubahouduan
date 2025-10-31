from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.utils import timezone
from datetime import date
from django.db.models import Q
from apps.product.models import Product, Category
from apps.order.models import Order
from apps.shop.models import Shop
from apps.user.models import User

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
    fields = ['name', 'description', 'price', 'original_price', 'stock_quantity', 
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
    fields = ['name', 'description', 'price', 'original_price', 'stock_quantity', 
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

class OrderListView(MerchantRequiredMixin, ListView):
    model = Order
    template_name = 'merchant/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_queryset(self):
        return Order.objects.all().order_by('-created_at')