import requests
from urllib.parse import urlencode
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class WeChatService:
    def __init__(self):
        self.app_id = settings.WECHAT_APP_ID
        self.app_secret = settings.WECHAT_APP_SECRET
        self.base_url = "https://api.weixin.qq.com"
    
    def get_auth_url(self, redirect_uri, scope="snsapi_userinfo", state=""):
        """生成微信授权URL"""
        base_url = "https://open.weixin.qq.com/connect/oauth2/authorize"
        params = {
            "appid": self.app_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state
        }
        return f"{base_url}?{urlencode(params)}#wechat_redirect"
    
    def get_access_token(self, code):
        """通过code获取access_token"""
        url = f"{self.base_url}/sns/oauth2/access_token"
        params = {
            "appid": self.app_id,
            "secret": self.app_secret,
            "code": code,
            "grant_type": "authorization_code"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            logger.info(f"WeChat access_token response: {result}")
            return result
        except Exception as e:
            logger.error(f"WeChat access_token error: {e}")
            return {'errcode': -1, 'errmsg': str(e)}
    
    def get_user_info(self, access_token, openid):
        """获取微信用户信息"""
        url = f"{self.base_url}/sns/userinfo"
        params = {
            "access_token": access_token,
            "openid": openid,
            "lang": "zh_CN"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            logger.info(f"WeChat user_info response: {result}")
            return result
        except Exception as e:
            logger.error(f"WeChat user_info error: {e}")
            return {'errcode': -1, 'errmsg': str(e)}
    
    def refresh_access_token(self, refresh_token):
        """刷新access_token"""
        url = f"{self.base_url}/sns/oauth2/refresh_token"
        params = {
            "appid": self.app_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            return response.json()
        except Exception as e:
            logger.error(f"WeChat refresh_token error: {e}")
            return {'errcode': -1, 'errmsg': str(e)}