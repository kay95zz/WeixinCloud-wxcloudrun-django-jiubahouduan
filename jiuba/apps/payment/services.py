import time
import hashlib
import random
import requests
from django.conf import settings
from django.utils import timezone

class WeChatPayService:
    """
    微信支付服务类
    ---
    **当前状态**：模拟版本，用于开发和测试
    **切换正式**：取消注释正式代码，配置微信支付参数
    """
    
    def __init__(self):
        # 模拟配置 - 正式使用时需要在settings.py中配置真实参数
        self.appid = getattr(settings, 'WECHAT_APPID', 'wx_your_appid')
        self.mch_id = getattr(settings, 'WECHAT_MCH_ID', '1230000109')
        self.api_key = getattr(settings, 'WECHAT_API_KEY', 'your_api_key_here')
        self.notify_url = getattr(settings, 'WECHAT_NOTIFY_URL', 'https://yourdomain.com/api/payments/wechat_callback/')
    
    def unified_order(self, payment):
        """
        微信支付统一下单
        ---
        **模拟版本**：生成模拟支付参数，前端可正常调起支付界面
        **正式版本**：调用微信支付API，需要商户证书和签名验证
        """
        # ==================== 模拟代码（当前使用） ====================
        try:
            # 模拟生成预支付ID
            prepay_id = f"wx{int(time.time())}{random.randint(1000, 9999)}"
            
            # 生成前端支付参数
            pay_params = self._generate_pay_params(prepay_id)
            return {
                'success': True,
                'payment_data': pay_params
            }
            
        except Exception as e:
            return {'success': False, 'error': f'微信支付下单失败: {str(e)}'}
        
        # ==================== 正式微信支付代码（需要时取消注释） ====================
        """
        try:
            # 构造请求参数
            params = {
                'appid': self.appid,
                'mch_id': self.mch_id,
                'nonce_str': self._generate_nonce_str(),
                'body': f'订单支付-{payment.order.id}',
                'out_trade_no': payment.out_trade_no,
                'total_fee': int(payment.amount * 100),  # 单位：分
                'spbill_create_ip': self._get_client_ip(),
                'notify_url': self.notify_url,
                'trade_type': 'JSAPI',
                'openid': payment.user.wechat_openid  # 需要用户有微信openid
            }
            
            # 生成签名
            params['sign'] = self._generate_real_sign(params)
            
            # 调用微信支付统一下单API
            response = requests.post(
                'https://api.mch.weixin.qq.com/pay/unifiedorder',
                data=self._dict_to_xml(params),
                headers={'Content-Type': 'application/xml'},
                timeout=10
            )
            
            # 解析XML响应
            result = self._xml_to_dict(response.content)
            
            if result.get('return_code') == 'SUCCESS' and result.get('result_code') == 'SUCCESS':
                prepay_id = result['prepay_id']
                pay_params = self._generate_pay_params(prepay_id)
                return {
                    'success': True,
                    'payment_data': pay_params
                }
            else:
                error_msg = result.get('return_msg') or result.get('err_code_des', '微信支付下单失败')
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            return {'success': False, 'error': f'微信支付下单失败: {str(e)}'}
        """
    
    def _generate_pay_params(self, prepay_id):
        """生成前端支付参数"""
        timestamp = str(int(time.time()))
        nonce_str = self._generate_nonce_str()
        
        params = {
            'appId': self.appid,
            'timeStamp': timestamp,
            'nonceStr': nonce_str,
            'package': f'prepay_id={prepay_id}',
            'signType': 'MD5'
        }
        
        # 模拟签名
        pay_sign = "模拟签名"
        # 正式签名：pay_sign = self._generate_real_sign(params)
        
        params['paySign'] = pay_sign
        return params
    
    def process_refund(self, payment, reason):
        """
        处理微信支付退款
        ---
        **模拟版本**：直接返回退款成功
        **正式版本**：需要商户证书，调用微信支付退款API
        """
        # ==================== 模拟代码 ====================
        try:
            print(f"模拟微信支付退款: {payment.out_trade_no}, 原因: {reason}")
            return {'success': True, 'message': '退款成功'}
        except Exception as e:
            return {'success': False, 'error': f'退款失败: {str(e)}'}
        
        # ==================== 正式微信支付退款代码 ====================
        """
        try:
            # 构造退款请求参数
            params = {
                'appid': self.appid,
                'mch_id': self.mch_id,
                'nonce_str': self._generate_nonce_str(),
                'transaction_id': payment.transaction_id,
                'out_refund_no': f"REFUND{payment.out_trade_no}",
                'total_fee': int(payment.amount * 100),
                'refund_fee': int(payment.amount * 100),
                'refund_desc': reason[:80]  # 限制长度
            }
            
            params['sign'] = self._generate_real_sign(params)
            
            # 需要证书的请求
            response = requests.post(
                'https://api.mch.weixin.qq.com/secapi/pay/refund',
                data=self._dict_to_xml(params),
                cert=(
                    settings.WECHAT_CERT_PATH,  # 证书路径
                    settings.WECHAT_KEY_PATH    # 密钥路径
                ),
                headers={'Content-Type': 'application/xml'},
                timeout=10
            )
            
            result = self._xml_to_dict(response.content)
            
            if result.get('return_code') == 'SUCCESS' and result.get('result_code') == 'SUCCESS':
                return {'success': True, 'message': '退款成功'}
            else:
                error_msg = result.get('return_msg') or result.get('err_code_des', '退款失败')
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            return {'success': False, 'error': f'退款失败: {str(e)}'}
        """
    
    def query_order(self, out_trade_no):
        """
        查询订单支付状态
        """
        # ==================== 模拟代码 ====================
        return {
            'success': True, 
            'trade_state': 'SUCCESS', 
            'transaction_id': f'trans{int(time.time())}'
        }
        
        # ==================== 正式查询代码 ====================
        """
        try:
            params = {
                'appid': self.appid,
                'mch_id': self.mch_id,
                'out_trade_no': out_trade_no,
                'nonce_str': self._generate_nonce_str()
            }
            
            params['sign'] = self._generate_real_sign(params)
            
            response = requests.post(
                'https://api.mch.weixin.qq.com/pay/orderquery',
                data=self._dict_to_xml(params),
                headers={'Content-Type': 'application/xml'},
                timeout=5
            )
            
            result = self._xml_to_dict(response.content)
            
            if result.get('return_code') == 'SUCCESS':
                return {
                    'success': True,
                    'trade_state': result.get('trade_state'),
                    'transaction_id': result.get('transaction_id')
                }
            else:
                return {'success': False, 'error': result.get('return_msg', '查询失败')}
                
        except Exception as e:
            return {'success': False, 'error': f'查询失败: {str(e)}'}
        """
    
    def _generate_real_sign(self, params):
        """正式微信支付签名生成"""
        # 按照参数名ASCII字典序排序
        sorted_params = sorted(params.items())
        # 拼接成URL键值对格式
        string_a = '&'.join([f"{k}={v}" for k, v in sorted_params if v and k != 'sign'])
        # 拼接API密钥
        string_sign_temp = f"{string_a}&key={self.api_key}"
        # MD5加密并转大写
        sign = hashlib.md5(string_sign_temp.encode('utf-8')).hexdigest().upper()
        return sign
    
    def _generate_nonce_str(self, length=32):
        """生成随机字符串"""
        chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _get_client_ip(self):
        """获取客户端IP（简化）"""
        return '127.0.0.1'
    
    def _dict_to_xml(self, params):
        """字典转XML - 正式微信支付使用"""
        xml = ['<xml>']
        for k, v in params.items():
            xml.append(f'<{k}><![CDATA[{v}]]></{k}>')
        xml.append('</xml>')
        return ''.join(xml)
    
    def _xml_to_dict(self, xml_content):
        """XML转字典 - 正式微信支付使用"""
        # 这里需要实现XML解析逻辑
        # 可以使用xml.etree.ElementTree等库
        return {'return_code': 'SUCCESS', 'prepay_id': '真实预支付ID'}


class BalancePayService:
    """
    余额支付服务类
    ---
    **功能完整**：余额支付逻辑相对简单，可以直接使用
    """
    
    def process_payment(self, payment):
        """
        处理余额支付
        """
        user = payment.user
        
        # 检查用户余额
        user_balance = getattr(user, 'balance', 0)
        if user_balance >= payment.amount:
            try:
                # 扣减余额
                user.balance -= payment.amount
                user.save()
                
                # 更新支付状态
                payment.status = 'success'
                payment.paid_at = timezone.now()
                payment.save()
                
                # 更新订单状态
                order = payment.order
                order.status = 'paid'
                order.save()
                
                return {'success': True, 'message': '支付成功'}
            except Exception as e:
                payment.status = 'failed'
                payment.save()
                return {'success': False, 'error': f'支付处理失败: {str(e)}'}
        else:
            payment.status = 'failed'
            payment.save()
            return {'success': False, 'error': '余额不足'}
    
    def process_refund(self, payment, reason):
        """
        处理余额支付退款
        """
        try:
            user = payment.user
            
            # 退还余额
            user.balance += payment.amount
            user.save()
            
            return {'success': True, 'message': '退款成功'}
        except Exception as e:
            return {'success': False, 'error': f'退款失败: {str(e)}'}