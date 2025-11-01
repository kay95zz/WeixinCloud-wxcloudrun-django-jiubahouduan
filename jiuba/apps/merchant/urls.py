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
    path('orders/', views.MerchantOrderListView.as_view(), name='order_list'),
    # 活动/预约管理
    path('activities/', views.ActivityListView.as_view(), name='activity_list'),
    path('activities/add/', views.ActivityCreateView.as_view(), name='activity_add'),
    path('activities/<int:pk>/edit/', views.ActivityUpdateView.as_view(), name='activity_edit'),
    path('activities/<int:pk>/delete/', views.ActivityDeleteView.as_view(), name='activity_delete'),
    path('activities/<int:pk>/', views.ActivityDetailView.as_view(), name='activity_detail'),
    path('reservations/', views.MerchantReservationListView.as_view(), name='reservation_list'),
    path('activities/<int:pk>/reservations/', views.MerchantActivityReservationView.as_view(), name='activity_reservations'),
    path('reservations/<int:reservation_id>/complete/', views.CompleteReservationView.as_view(), name='complete_reservation'),
    # 店铺管理
    path('shops/', views.ShopListView.as_view(), name='shop_list'),
    path('shops/<int:pk>/edit/', views.ShopUpdateView.as_view(), name='shop_edit'),
    path('shops/<int:pk>/', views.ShopDetailView.as_view(), name='shop_detail'),
    # 公告管理
    path('notices/', views.NoticeListView.as_view(), name='notice_list'),
    path('notices/add/', views.NoticeCreateView.as_view(), name='notice_add'),
    path('notices/<int:pk>/edit/', views.NoticeUpdateView.as_view(), name='notice_edit'),
    path('notices/<int:pk>/delete/', views.NoticeDeleteView.as_view(), name='notice_delete'),
    path('notices/<int:pk>/', views.NoticeDetailView.as_view(), name='notice_detail'),
]