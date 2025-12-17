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
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

# 微信云托管支付配置
WECHAT_CLOUD_API_BASE = "http://api.weixin.qq.com/_/pay"
WECHAT_CLOUD_CALLBACK_PATH = "/api/payment/wechat/callback/"

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
        self.merchant_key = getattr(settings, 'WECHAT_MERCHANT_KEY', '')
        self.service_name = getattr(settings, 'WECHAT_CLOUD_SERVICE', 'default')
        
        if not all([self.env_id, self.merchant_id, self.app_id]):
            logger.warning("微信支付配置不完整，请检查环境变量设置")
    
    def _make_request(self, endpoint, data):
        """
        向微信云托管支付接口发送请求
        """
        url = f"{WECHAT_CLOUD_API_BASE}/{endpoint}"
        
        try:
            logger.info(f"微信支付请求: {url}, 数据: {json.dumps(data, ensure_ascii=False)}")
            
            response = requests.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            logger.info(f"微信支付响应状态: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            logger.info(f"微信支付响应数据: {json.dumps(result, ensure_ascii=False)}")
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"微信支付请求超时: {url}")
            raise Exception("支付请求超时，请稍后重试")
        except requests.exceptions.ConnectionError:
            logger.error(f"微信支付连接错误: {url}")
            raise Exception("支付服务连接失败")
        except requests.exceptions.HTTPError as e:
            logger.error(f"微信支付HTTP错误: {e.response.status_code if hasattr(e, 'response') else 'Unknown'}")
            raise Exception("支付服务异常")
        except Exception as e:
            logger.error(f"微信支付请求失败: {str(e)}, URL: {url}")
            raise
    
    def unified_order(self, order, openid, request_ip, notify_url=None):
        """
        统一下单
        :param order: 订单对象
        :param openid: 用户OpenID
        :param request_ip: 用户IP地址
        :param notify_url: 回调URL（可选）
        :return: 支付配置
        """
        try:
            # 生成随机字符串
            nonce_str = str(uuid.uuid4()).replace('-', '')[:32]
            
            # 构造请求数据
            data = {
                "openid": openid,
                "sub_appid": self.app_id,
                "sub_mch_id": self.merchant_id,
                "body": f"{order.shop.name}-订单{order.order_number[-8:]}",
                "out_trade_no": order.order_number,
                "total_fee": int(float(order.total_amount) * 100),  # 转换为分
                "spbill_create_ip": request_ip,
                "notify_url": notify_url or f"{getattr(settings, 'SITE_URL', '')}{WECHAT_CLOUD_CALLBACK_PATH}",
                "trade_type": "JSAPI",
                "nonce_str": nonce_str,
                "time_start": timezone.now().strftime("%Y%m%d%H%M%S"),
                "time_expire": (timezone.now() + timezone.timedelta(minutes=30)).strftime("%Y%m%d%H%M%S"),
                "env_id": self.env_id,
                "callback_type": 2,
                "container": {
                    "service": self.service_name,
                    "path": "/pay/callback"
                }
            }
            
            logger.info(f"统一下单请求数据: {json.dumps(data, ensure_ascii=False)}")
            
            # 调用统一下单接口
            result = self._make_request("unifiedOrder", data)
            
            if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
                prepay_id = result.get("prepay_id")
                
                if not prepay_id:
                    logger.error(f"统一下单返回无prepay_id: {result}")
                    return {
                        "success": False,
                        "message": "支付参数获取失败"
                    }
                
                # 生成时间戳
                timestamp = str(int(timezone.now().timestamp()))
                
                # 构造小程序支付参数
                pay_config = {
                    "appId": self.app_id,
                    "timeStamp": timestamp,
                    "nonceStr": nonce_str,
                    "package": f"prepay_id={prepay_id}",
                    "signType": "MD5",
                }
                
                # 生成签名
                pay_config["paySign"] = self._generate_pay_sign(pay_config)
                
                logger.info(f"统一下单成功, prepay_id: {prepay_id}")
                
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
                logger.error(f"统一下单失败: {error_code} - {error_msg}")
                
                return {
                    "success": False,
                    "error_code": error_code,
                    "message": error_msg
                }
                
        except Exception as e:
            logger.error(f"统一下单异常: {str(e)}", exc_info=True)
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
                raise ValueError("必须提供transaction_id或out_trade_no")
            
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
            logger.error(f"查询订单异常: {str(e)}")
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
            logger.error(f"关闭订单异常: {str(e)}")
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
            logger.error(f"申请退款异常: {str(e)}")
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
                raise ValueError("必须提供退款单号、订单号或交易号")
            
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
            logger.error(f"查询退款异常: {str(e)}")
            return {
                "success": False,
                "message": f"查询退款失败: {str(e)}"
            }
    
    def _generate_pay_sign(self, data):
        """
        生成支付签名
        """
        try:
            # 按字典序排序参数
            sorted_items = sorted(data.items())
            
            # 拼接字符串
            string_to_sign = '&'.join([f"{k}={v}" for k, v in sorted_items])
            string_to_sign += f"&key={self.merchant_key}"
            
            # MD5加密
            md5 = hashlib.md5()
            md5.update(string_to_sign.encode('utf-8'))
            sign = md5.hexdigest().upper()
            
            return sign
            
        except Exception as e:
            logger.error(f"生成签名失败: {str(e)}")
            return ""
    
    def verify_signature(self, data, sign):
        """
        验证签名
        """
        try:
            # 移除sign字段
            if 'sign' in data:
                data_copy = data.copy()
                del data_copy['sign']
            else:
                data_copy = data
            
            # 按字典序排序
            sorted_items = sorted(data_copy.items())
            
            # 拼接字符串
            string_to_sign = '&'.join([f"{k}={v}" for k, v in sorted_items])
            string_to_sign += f"&key={self.merchant_key}"
            
            # MD5加密
            md5 = hashlib.md5()
            md5.update(string_to_sign.encode('utf-8'))
            calculated_sign = md5.hexdigest().upper()
            
            return calculated_sign == sign.upper()
            
        except Exception as e:
            logger.error(f"验证签名异常: {str(e)}")
            return False
    
    def handle_callback(self, callback_data):
        """
        处理支付回调
        """
        try:
            logger.info(f"收到支付回调: {json.dumps(callback_data, ensure_ascii=False)}")
            
            # 验证签名
            sign = callback_data.get('sign')
            if not sign or not self.verify_signature(callback_data, sign):
                logger.error("支付回调签名验证失败")
                return {
                    "success": False,
                    "message": "签名验证失败"
                }
            
            # 检查返回状态
            return_code = callback_data.get('return_code')
            if return_code != 'SUCCESS':
                logger.warning(f"支付回调返回失败: {callback_data.get('return_msg')}")
                return {
                    "success": True,  # 仍然返回成功，避免微信重复回调
                    "message": "支付失败"
                }
            
            # 获取关键信息
            result_code = callback_data.get('result_code')
            out_trade_no = callback_data.get('out_trade_no')
            transaction_id = callback_data.get('transaction_id')
            total_fee = callback_data.get('total_fee')
            
            logger.info(f"支付回调处理: out_trade_no={out_trade_no}, result_code={result_code}")
            
            return {
                "success": True,
                "out_trade_no": out_trade_no,
                "transaction_id": transaction_id,
                "total_fee": int(total_fee) / 100 if total_fee else 0,
                "result_code": result_code,
                "callback_data": callback_data
            }
            
        except Exception as e:
            logger.error(f"处理支付回调异常: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"处理回调异常: {str(e)}"
            }

# 全局支付实例
wechat_pay = WeChatPay()