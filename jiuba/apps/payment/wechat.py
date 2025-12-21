"""
微信支付模块 - 微信云托管版本
"""
import json
import requests
import hashlib
import uuid
import logging
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)

# 微信云托管支付配置
WECHAT_CLOUD_API_BASE = "http://api.weixin.qq.com/_/pay"

class WeChatPay:
    """微信支付类 - 云托管版本"""
    
    def __init__(self, env_id=None):
        """
        初始化微信支付
        :param env_id: 云托管环境ID
        """
        self.env_id = env_id or getattr(settings, 'WECHAT_CLOUD_ENV_ID', '')
        self.merchant_id = getattr(settings, 'WECHAT_MERCHANT_ID', '')
        self.app_id = getattr(settings, 'WECHAT_APP_ID', '')
        
        # 检查配置
        if not all([self.env_id, self.merchant_id, self.app_id]):
            logger.warning("⚠️ 微信支付配置不完整，请检查环境变量设置")
        else:
            logger.info("✅ 微信支付配置检查通过")
    
    def _make_request(self, endpoint, data):
        """
        向微信云托管支付接口发送请求
        """
        url = f"{WECHAT_CLOUD_API_BASE}/{endpoint}"
        
        try:
            logger.info(f"📤 微信支付请求: {endpoint}")
            
            response = requests.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            response.raise_for_status()
            result = response.json()
            logger.info(f"📥 微信支付响应: {result.get('return_code', 'UNKNOWN')}")
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error("⏰ 微信支付请求超时")
            raise Exception("支付请求超时，请稍后重试")
        except Exception as e:
            logger.error(f"❌ 微信支付请求失败: {str(e)}")
            raise Exception(f"支付服务异常: {str(e)}")
    
    def unified_order(self, order, openid, client_ip):
        """
        统一下单 - 云托管版本
        符合微信云托管开放接口服务要求
        """
        try:
            # 生成随机字符串
            nonce_str = str(uuid.uuid4()).replace('-', '')[:32]
            
            # 构建请求数据 - 严格按云托管要求
            data = {
                "openid": openid,
                "sub_appid": self.app_id,
                "sub_mch_id": self.merchant_id,
                "body": f"订单{order.order_number[-8:]}",
                "out_trade_no": order.order_number,
                "total_fee": int(float(order.total_amount) * 100),  # 转换为分
                "spbill_create_ip": client_ip,
                "trade_type": "JSAPI",
                "nonce_str": nonce_str,
                "time_start": timezone.now().strftime("%Y%m%d%H%M%S"),
                "time_expire": (timezone.now() + timezone.timedelta(minutes=30)).strftime("%Y%m%d%H%M%S"),
                "env_id": self.env_id,
                "callback_type": 2,
                "container": {
                    "service": "django-98",  # 你的服务名称
                    "path": "/api/payment/wechat/callback/"
                }
            }
            
            logger.info(f"🔄 统一下单数据: {json.dumps(data, ensure_ascii=False)}")
            
            # 调用统一下单接口
            result = self._make_request("unifiedOrder", data)
            
            # 检查返回结果
            return_code = result.get("return_code")
            result_code = result.get("result_code")
            
            if return_code == "SUCCESS" and result_code == "SUCCESS":
                prepay_id = result.get("prepay_id")
                
                if not prepay_id:
                    logger.error("❌ 统一下单返回无prepay_id")
                    return {
                        "success": False,
                        "message": "支付参数获取失败"
                    }
                
                # 生成时间戳
                timestamp = str(int(timezone.now().timestamp()))
                
                # 生成小程序支付参数
                pay_config = {
                    "appId": self.app_id,
                    "timeStamp": timestamp,
                    "nonceStr": nonce_str,
                    "package": f"prepay_id={prepay_id}",
                    "signType": "MD5",
                }
                
                # 注意：云托管不需要生成paySign，小程序端会自己生成
                
                logger.info(f"✅ 统一下单成功, prepay_id: {prepay_id}")
                
                return {
                    "success": True,
                    "prepay_id": prepay_id,
                    "payment": pay_config,
                    "order_number": order.order_number,
                    "message": "统一下单成功"
                }
            else:
                error_code = result.get("err_code", "")
                error_msg = result.get("err_code_des") or result.get("return_msg") or "统一下单失败"
                logger.error(f"❌ 统一下单失败: {error_code} - {error_msg}")
                
                return {
                    "success": False,
                    "error_code": error_code,
                    "message": error_msg
                }
                
        except Exception as e:
            logger.error(f"❌ 统一下单异常: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"统一下单异常: {str(e)}"
            }
    
    def query_order(self, transaction_id=None, out_trade_no=None):
        """
        查询订单状态
        """
        try:
            if not transaction_id and not out_trade_no:
                return {
                    "success": False,
                    "message": "必须提供transaction_id或out_trade_no"
                }
            
            data = {
                "sub_mch_id": self.merchant_id,
                "nonce_str": str(uuid.uuid4()).replace('-', '')[:32]
            }
            
            if transaction_id:
                data["transaction_id"] = transaction_id
            elif out_trade_no:
                data["out_trade_no"] = out_trade_no
            
            result = self._make_request("queryOrder", data)
            
            if result.get("return_code") == "SUCCESS":
                return {
                    "success": True,
                    "data": result,
                    "trade_state": result.get("trade_state"),
                    "trade_state_desc": result.get("trade_state_desc")
                }
            else:
                return {
                    "success": False,
                    "message": result.get("return_msg", "查询失败")
                }
                
        except Exception as e:
            logger.error(f"❌ 查询订单异常: {str(e)}")
            return {
                "success": False,
                "message": f"查询失败: {str(e)}"
            }
    
    def close_order(self, out_trade_no):
        """
        关闭订单
        """
        try:
            data = {
                "sub_mch_id": self.merchant_id,
                "out_trade_no": out_trade_no,
                "nonce_str": str(uuid.uuid4()).replace('-', '')[:32]
            }
            
            result = self._make_request("closeOrder", data)
            
            if result.get("return_code") == "SUCCESS":
                return {
                    "success": True,
                    "data": result
                }
            else:
                return {
                    "success": False,
                    "message": result.get("return_msg", "关闭订单失败")
                }
                
        except Exception as e:
            logger.error(f"❌ 关闭订单异常: {str(e)}")
            return {
                "success": False,
                "message": f"关闭订单失败: {str(e)}"
            }
    
    def refund(self, order, refund_amount, refund_desc="", out_refund_no=None):
        """
        申请退款
        """
        try:
            if not order.transaction_id:
                return {
                    "success": False,
                    "message": "订单无交易号，无法退款"
                }
            
            data = {
                "sub_mch_id": self.merchant_id,
                "transaction_id": order.transaction_id,
                "out_trade_no": order.order_number,
                "out_refund_no": out_refund_no or f"RF{order.order_number}{int(timezone.now().timestamp() % 1000000)}",
                "total_fee": int(float(order.total_amount) * 100),
                "refund_fee": int(float(refund_amount) * 100),
                "refund_desc": refund_desc[:80] if refund_desc else "用户申请退款",
                "nonce_str": str(uuid.uuid4()).replace('-', '')[:32]
            }
            
            result = self._make_request("refund", data)
            
            if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
                return {
                    "success": True,
                    "data": result,
                    "refund_id": result.get("refund_id")
                }
            else:
                error_msg = result.get("err_code_des") or result.get("return_msg") or "退款失败"
                return {
                    "success": False,
                    "message": error_msg
                }
                
        except Exception as e:
            logger.error(f"❌ 申请退款异常: {str(e)}")
            return {
                "success": False,
                "message": f"退款申请异常: {str(e)}"
            }
    
    def query_refund(self, out_refund_no=None, out_trade_no=None, transaction_id=None):
        """
        查询退款状态
        """
        try:
            data = {
                "sub_mch_id": self.merchant_id,
                "nonce_str": str(uuid.uuid4()).replace('-', '')[:32]
            }
            
            if out_refund_no:
                data["out_refund_no"] = out_refund_no
            elif out_trade_no:
                data["out_trade_no"] = out_trade_no
            elif transaction_id:
                data["transaction_id"] = transaction_id
            else:
                return {
                    "success": False,
                    "message": "必须提供退款单号、订单号或交易号"
                }
            
            result = self._make_request("queryRefund", data)
            
            if result.get("return_code") == "SUCCESS":
                return {
                    "success": True,
                    "data": result
                }
            else:
                return {
                    "success": False,
                    "message": result.get("return_msg", "查询退款失败")
                }
                
        except Exception as e:
            logger.error(f"❌ 查询退款异常: {str(e)}")
            return {
                "success": False,
                "message": f"查询退款失败: {str(e)}"
            }
    
    def handle_callback(self, callback_data):
        """
        处理支付回调
        """
        try:
            logger.info(f"💰 收到支付回调: {json.dumps(callback_data, ensure_ascii=False)}")
            
            # 检查返回状态
            return_code = callback_data.get('return_code')
            if return_code != 'SUCCESS':
                logger.warning(f"⚠️ 支付回调返回失败: {callback_data.get('return_msg')}")
                # 仍然返回成功，避免微信重复回调
                return {
                    "errcode": 0,
                    "errmsg": "OK"
                }
            
            # 获取关键信息
            result_code = callback_data.get('result_code')
            out_trade_no = callback_data.get('out_trade_no')
            transaction_id = callback_data.get('transaction_id')
            
            logger.info(f"🔄 支付回调处理: out_trade_no={out_trade_no}, result_code={result_code}")
            
            # 必须返回这个格式，否则会重复回调
            return {
                "errcode": 0,
                "errmsg": "OK"
            }
            
        except Exception as e:
            logger.error(f"❌ 处理支付回调异常: {str(e)}", exc_info=True)
            # 发生异常也必须返回成功格式
            return {
                "errcode": 0,
                "errmsg": "OK"
            }

# 全局支付实例
wechat_pay = WeChatPay()