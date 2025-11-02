# apps/user/wechat_service.py
import requests
from urllib.parse import urlencode
from django.conf import settings
import logging
import certifi

logger = logging.getLogger(__name__)

class WeChatService:
    def __init__(self):
        self.app_id = settings.WECHAT_APP_ID
        self.app_secret = settings.WECHAT_APP_SECRET
        self.base_url = "https://api.weixin.qq.com"
    
    def get_access_token(self, code):
        """通过code获取access_token - 生产环境安全版本"""
        url = f"{self.base_url}/sns/oauth2/access_token"
        params = {
            "appid": self.app_id,
            "secret": self.app_secret,
            "code": code,
            "grant_type": "authorization_code"
        }
        
        try:
            # 使用 certifi 证书包进行安全验证
            response = requests.get(
                url, 
                params=params, 
                timeout=10, 
                verify=certifi.where()  # 使用权威证书验证
            )
            result = response.json()
            logger.info(f"WeChat access_token response: {result}")
            return result
        except requests.exceptions.SSLError as e:
            logger.error(f"微信API SSL证书验证失败: {e}")
            # 生产环境不应该降级到不安全模式
            return {'errcode': -1, 'errmsg': 'SSL证书验证失败'}
        except Exception as e:
            logger.error(f"WeChat access_token error: {e}")
            return {'errcode': -1, 'errmsg': str(e)}
    
    def get_user_info(self, access_token, openid):
        """获取微信用户信息 - 生产环境安全版本"""
        url = f"{self.base_url}/sns/userinfo"
        params = {
            "access_token": access_token,
            "openid": openid,
            "lang": "zh_CN"
        }
        
        try:
            response = requests.get(
                url, 
                params=params, 
                timeout=10, 
                verify=certifi.where()  # 使用权威证书验证
            )
            result = response.json()
            logger.info(f"WeChat user_info response: {result}")
            return result
        except requests.exceptions.SSLError as e:
            logger.error(f"微信API SSL证书验证失败: {e}")
            return {'errcode': -1, 'errmsg': 'SSL证书验证失败'}
        except Exception as e:
            logger.error(f"WeChat user_info error: {e}")
            return {'errcode': -1, 'errmsg': str(e)}