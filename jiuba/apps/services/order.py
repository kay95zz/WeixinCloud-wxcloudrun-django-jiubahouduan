from fastapi import HTTPException
from sqlalchemy.orm import Session
from redis import Redis
import json

from apps.models import Order, OrderItem, User
from apps.schemas import OrderCreate, OrderItemCreate

class CartService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    def get_cart_key(self, user_id: int, shop_id: int):
        return f"cart:{user_id}:{shop_id}"
    
    def add_to_cart(self, user_id: int, shop_id: int, item_id: int, quantity: int = 1):
        """添加商品到购物车"""
        cart_key = self.get_cart_key(user_id, shop_id)
        current_cart = self.redis.hgetall(cart_key)
        
        if str(item_id) in current_cart:
            current_quantity = int(current_cart[str(item_id)])
            quantity += current_quantity
        
        self.redis.hset(cart_key, item_id, quantity)
        return True
    
    def get_cart(self, user_id: int, shop_id: int):
        """获取购物车内容"""
        cart_key = self.get_cart_key(user_id, shop_id)
        return self.redis.hgetall(cart_key)
    
    def clear_cart(self, user_id: int, shop_id: int):
        """清空购物车"""
        cart_key = self.get_cart_key(user_id, shop_id)
        self.redis.delete(cart_key)

class OrderService:
    def __init__(self, db: Session, cart_service: CartService):
        self.db = db
        self.cart_service = cart_service
    
    def create_order_from_cart(self, user_id: int, shop_id: int):
        """从购物车创建订单"""
        # 获取购物车内容
        cart = self.cart_service.get_cart(user_id, shop_id)
        if not cart:
            raise HTTPException(status_code=400, detail="Cart is empty")
        
        # 计算总金额
        total_amount = 0
        order_items = []
        
        for item_id_str, quantity in cart.items():
            item_id = int(item_id_str)
            item = self.db.query(Item).filter(Item.id == item_id).first()
            if not item:
                continue
            
            item_total = item.price * int(quantity)
            total_amount += item_total
            
            order_items.append(OrderItemCreate(
                item_id=item_id,
                quantity=int(quantity),
                price=item.price
            ))
        
        # 创建订单
        order_data = OrderCreate(
            user_id=user_id,
            shop_id=shop_id,
            total_amount=total_amount,
            items=order_items
        )
        
        # 保存订单到数据库
        db_order = Order(
            user_id=order_data.user_id,
            shop_id=order_data.shop_id,
            total_amount=order_data.total_amount,
            status="pending"
        )
        self.db.add(db_order)
        self.db.flush()
        
        # 添加订单项
        for item in order_data.items:
            db_order_item = OrderItem(
                order_id=db_order.id,
                item_id=item.item_id,
                quantity=item.quantity,
                price=item.price
            )
            self.db.add(db_order_item)
        
        self.db.commit()
        self.db.refresh(db_order)
        
        # 清空购物车
        self.cart_service.clear_cart(user_id, shop_id)
        
        return db_order