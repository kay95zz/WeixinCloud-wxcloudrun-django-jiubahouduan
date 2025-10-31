from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer, AddToCartSerializer, UpdateCartItemSerializer
from apps.product.models import Product
from apps.shop.models import Shop

class CartViewSet(viewsets.ModelViewSet):
    """购物车视图集"""
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """获取当前用户的购物车"""
        return Cart.objects.filter(user=self.request.user)
    
    def get_cart_for_shop(self, shop_id):
        """获取或创建指定店铺的购物车"""
        shop = get_object_or_404(Shop, id=shop_id)
        cart, created = Cart.objects.get_or_create(
            user=self.request.user,
            shop=shop,
            defaults={'user': self.request.user, 'shop': shop}
        )
        return cart
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """添加商品到购物车"""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        
        product = get_object_or_404(Product, id=product_id, is_available=True, status='published')
        
        # 获取或创建购物车
        cart = self.get_cart_for_shop(product.shop.id)
        
        # 检查购物车中是否已有该商品
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                'quantity': quantity,
                'price': product.price
            }
        )
        
        if not created:
            # 如果已存在，则更新数量
            cart_item.quantity += quantity
            cart_item.save()
        
        return Response(CartItemSerializer(cart_item).data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def get_cart(self, request):
        """获取当前用户的购物车（根据店铺）"""
        shop_id = request.query_params.get('shop_id')
        if not shop_id:
            return Response({"error": "需要提供shop_id参数"}, status=status.HTTP_400_BAD_REQUEST)
        
        cart = self.get_cart_for_shop(shop_id)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'])
    def update_item(self, request):
        """更新购物车中商品的数量"""
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        item_id = request.data.get('item_id')
        quantity = serializer.validated_data['quantity']
        
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.quantity = quantity
        cart_item.save()
        
        return Response(CartItemSerializer(cart_item).data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        """从购物车中移除商品"""
        item_id = request.data.get('item_id')
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()
        
        return Response({"message": "商品已从购物车中移除"}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['delete'])
    def clear_cart(self, request):
        """清空购物车"""
        shop_id = request.data.get('shop_id')
        if not shop_id:
            return Response({"error": "需要提供shop_id参数"}, status=status.HTTP_400_BAD_REQUEST)
        
        cart = self.get_cart_for_shop(shop_id)
        cart.items.all().delete()
        
        return Response({"message": "购物车已清空"}, status=status.HTTP_200_OK)
