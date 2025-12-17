"""
支付服务模块
"""
import json
import logging
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from apps.order.models import Order
from apps.user.models import User
from .models import Payment
from .wechat import wechat_pay

logger = logging.getLogger(__name__)

class PaymentService:
    """支付服务类"""
    
    @staticmethod
    def create_payment_record(order, payment_method, amount=0, points=0, extra_data=None):
        """
        创建支付记录
        """
        try:
            payment = Payment.objects.create(
                user=order.user,
                order=order,
                payment_method=payment_method,
                amount=amount,
                points=points,
                status='pending',
                extra_data=json.dumps(extra_data) if extra_data else None
            )
            
            logger.info(f"创建支付记录成功: payment_id={payment.id}, order_id={order.id}")
            return payment
            
        except Exception as e:
            logger.error(f"创建支付记录失败: {str(e)}")
            raise
    
    @staticmethod
    def process_wechat_payment(order, openid, client_ip):
        """
        处理微信支付
        """
        try:
            # 生成回调URL
            notify_url = f"{getattr(settings, 'SITE_URL', '')}/api/payment/wechat/callback/"
            
            # 调用统一下单
            result = wechat_pay.unified_order(
                order=order,
                openid=openid,
                request_ip=client_ip,
                notify_url=notify_url
            )
            
            if result['success']:
                # 创建支付记录
                payment = PaymentService.create_payment_record(
                    order=order,
                    payment_method='wechat',
                    amount=order.total_amount,
                    extra_data={
                        'prepay_id': result['prepay_id'],
                        'payment_config': result['payment']
                    }
                )
                
                return {
                    "success": True,
                    "payment": payment,
                    "payment_config": result['payment'],
                    "order_number": order.order_number
                }
            else:
                return {
                    "success": False,
                    "message": result['message'],
                    "error_code": result.get('error_code')
                }
                
        except Exception as e:
            logger.error(f"处理微信支付失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"支付处理失败: {str(e)}"
            }
    
    @staticmethod
    def process_balance_payment(order):
        """
        处理余额支付
        """
        try:
            user = order.user
            
            with transaction.atomic():
                # 锁定用户记录
                user = User.objects.select_for_update().get(id=user.id)
                
                # 检查余额
                if float(user.balance) < float(order.total_amount):
                    return {
                        "success": False,
                        "message": "余额不足"
                    }
                
                # 扣除余额
                user.balance -= order.total_amount
                user.save()
                
                # 创建支付记录
                payment = PaymentService.create_payment_record(
                    order=order,
                    payment_method='balance',
                    amount=order.total_amount
                )
                
                # 更新支付状态
                payment.status = 'paid'
                payment.paid_at = timezone.now()
                payment.save()
                
                # 更新订单状态
                order.is_paid = True
                order.paid_at = timezone.now()
                order.payment_method = 'balance'
                order.save()
                
                logger.info(f"余额支付成功: order_id={order.id}, payment_id={payment.id}")
                
                return {
                    "success": True,
                    "payment": payment,
                    "balance": float(user.balance)
                }
                
        except Exception as e:
            logger.error(f"处理余额支付失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"余额支付失败: {str(e)}"
            }
    
    @staticmethod
    def process_points_payment(order):
        """
        处理积分支付
        """
        try:
            user = order.user
            
            with transaction.atomic():
                # 锁定用户记录
                user = User.objects.select_for_update().get(id=user.id)
                
                # 检查积分是否足够
                if user.points < order.total_points:
                    return {
                        "success": False,
                        "message": "积分不足"
                    }
                
                # 扣除积分
                user.points -= order.total_points
                user.save()
                
                # 创建支付记录
                payment = PaymentService.create_payment_record(
                    order=order,
                    payment_method='points',
                    amount=0,
                    points=order.total_points
                )
                
                # 更新支付状态
                payment.status = 'paid'
                payment.paid_at = timezone.now()
                payment.save()
                
                # 更新订单状态
                order.is_paid = True
                order.paid_at = timezone.now()
                order.payment_method = 'points'
                order.save()
                
                logger.info(f"积分支付成功: order_id={order.id}, payment_id={payment.id}")
                
                return {
                    "success": True,
                    "payment": payment,
                    "points": user.points
                }
                
        except Exception as e:
            logger.error(f"处理积分支付失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"积分支付失败: {str(e)}"
            }
    
    @staticmethod
    def query_payment_status(order):
        """
        查询支付状态
        """
        try:
            payment = Payment.objects.filter(order=order).first()
            
            if not payment:
                return {
                    "success": False,
                    "message": "支付记录不存在"
                }
            
            # 如果是微信支付且状态为待支付，查询微信支付状态
            if payment.payment_method == 'wechat' and payment.status == 'pending':
                result = wechat_pay.query_order(out_trade_no=order.order_number)
                
                if result['success'] and result['trade_state'] == 'SUCCESS':
                    # 支付成功，更新状态
                    PaymentService.update_payment_success(
                        payment=payment,
                        transaction_id=result['data'].get('transaction_id')
                    )
            
            return {
                "success": True,
                "payment_status": payment.status,
                "payment_method": payment.payment_method,
                "paid_at": payment.paid_at,
                "order_status": order.status
            }
            
        except Exception as e:
            logger.error(f"查询支付状态失败: {str(e)}")
            return {
                "success": False,
                "message": f"查询支付状态失败: {str(e)}"
            }
    
    @staticmethod
    def update_payment_success(payment, transaction_id=None):
        """
        更新支付成功状态
        """
        try:
            with transaction.atomic():
                payment.status = 'paid'
                payment.paid_at = timezone.now()
                if transaction_id:
                    payment.transaction_id = transaction_id
                payment.save()
                
                # 更新订单状态
                order = payment.order
                order.is_paid = True
                order.paid_at = payment.paid_at
                order.payment_method = payment.payment_method
                if transaction_id:
                    order.transaction_id = transaction_id
                order.save()
                
                logger.info(f"更新支付成功状态: payment_id={payment.id}, order_id={order.id}")
                
                return True
                
        except Exception as e:
            logger.error(f"更新支付成功状态失败: {str(e)}")
            return False
    
    @staticmethod
    def process_refund(order, refund_amount, refund_desc="", refund_reason=""):
        """
        处理退款
        """
        try:
            payment = Payment.objects.filter(order=order, status='paid').first()
            
            if not payment:
                return {
                    "success": False,
                    "message": "未找到已支付的订单"
                }
            
            # 检查退款金额
            if float(refund_amount) > float(payment.amount):
                return {
                    "success": False,
                    "message": "退款金额不能超过支付金额"
                }
            
            # 根据支付方式处理退款
            if payment.payment_method == 'wechat':
                return PaymentService._process_wechat_refund(payment, refund_amount, refund_desc)
            elif payment.payment_method == 'balance':
                return PaymentService._process_balance_refund(payment, refund_amount, refund_desc, refund_reason)
            elif payment.payment_method == 'points':
                return PaymentService._process_points_refund(payment, refund_amount, refund_desc, refund_reason)
            else:
                return {
                    "success": False,
                    "message": "不支持的退款方式"
                }
                
        except Exception as e:
            logger.error(f"处理退款失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"退款处理失败: {str(e)}"
            }
    
    @staticmethod
    def _process_wechat_refund(payment, refund_amount, refund_desc):
        """
        处理微信退款
        """
        try:
            # 调用微信退款接口
            result = wechat_pay.refund(
                order=payment.order,
                refund_amount=refund_amount,
                refund_desc=refund_desc
            )
            
            if result['success']:
                # 更新支付状态
                payment.status = 'refunding'
                payment.refund_amount = refund_amount
                payment.refund_desc = refund_desc
                payment.save()
                
                return {
                    "success": True,
                    "refund_id": result['refund_id'],
                    "message": "退款申请已提交"
                }
            else:
                return {
                    "success": False,
                    "message": result['message']
                }
                
        except Exception as e:
            logger.error(f"处理微信退款失败: {str(e)}")
            return {
                "success": False,
                "message": f"微信退款失败: {str(e)}"
            }
    
    @staticmethod
    def _process_balance_refund(payment, refund_amount, refund_desc, refund_reason):
        """
        处理余额退款
        """
        try:
            with transaction.atomic():
                user = payment.user
                user = User.objects.select_for_update().get(id=user.id)
                
                # 返还余额
                user.balance += refund_amount
                user.save()
                
                # 更新支付状态
                payment.status = 'refunded'
                payment.refund_amount = refund_amount
                payment.refund_desc = refund_desc
                payment.refund_reason = refund_reason
                payment.refund_at = timezone.now()
                payment.save()
                
                logger.info(f"余额退款成功: payment_id={payment.id}, amount={refund_amount}")
                
                return {
                    "success": True,
                    "message": "退款成功",
                    "balance": float(user.balance)
                }
                
        except Exception as e:
            logger.error(f"处理余额退款失败: {str(e)}")
            return {
                "success": False,
                "message": f"余额退款失败: {str(e)}"
            }
    
    @staticmethod
    def _process_points_refund(payment, refund_amount, refund_desc, refund_reason):
        """
        处理积分退款
        """
        try:
            with transaction.atomic():
                user = payment.user
                user = User.objects.select_for_update().get(id=user.id)
                
                # 返还积分
                refund_points = int(refund_amount)  # 假设1积分=1元
                user.points += refund_points
                user.save()
                
                # 更新支付状态
                payment.status = 'refunded'
                payment.refund_amount = refund_amount
                payment.refund_desc = refund_desc
                payment.refund_reason = refund_reason
                payment.refund_at = timezone.now()
                payment.save()
                
                logger.info(f"积分退款成功: payment_id={payment.id}, points={refund_points}")
                
                return {
                    "success": True,
                    "message": "退款成功",
                    "points": user.points
                }
                
        except Exception as e:
            logger.error(f"处理积分退款失败: {str(e)}")
            return {
                "success": False,
                "message": f"积分退款失败: {str(e)}"
            }