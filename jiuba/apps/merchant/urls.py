from django.urls import path
from . import views

app_name = 'merchant'

urlpatterns = [
    # 登录退出
    path('login/', views.MerchantLoginView.as_view(), name='login'),
    path('logout/', views.merchant_logout, name='logout'),
    # 仪表盘
    path('', views.MerchantDashboardView.as_view(), name='dashboard'),
    # 用户管理
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/balance-points/', views.UserBalancePointsUpdateView.as_view(), name='user_balance_points'),
    # 商品管理
    path('product/', views.ProductListView.as_view(), name='product_list'),
    path('product/add/', views.ProductCreateView.as_view(), name='product_add'),
    path('product/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('product/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    # 订单管理
    path('order/', views.OrderListView.as_view(), name='order_list'),
]