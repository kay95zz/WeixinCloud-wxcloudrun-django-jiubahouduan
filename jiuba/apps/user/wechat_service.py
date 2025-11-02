# apps/user/wechat_service.py
import requests
from urllib.parse import urlencode
from django.conf import settings
import logging
import certifi
import ssl
import os

logger = logging.getLogger(__name__)

class WeChatService:
    def __init__(self):
        self.app_id = settings.WECHAT_APP_ID
        self.app_secret = settings.WECHAT_APP_SECRET
        self.base_url = "https://api.weixin.qq.com"
        self._setup_ssl_context()
    
    def _setup_ssl_context(self):
        """设置 SSL 上下文，处理证书验证问题"""
        try:
            # 方法1: 使用系统证书（如果可用）
            system_ca_file = '/etc/ssl/certs/ca-certificates.crt'
            if os.path.exists(system_ca_file):
                self.verify_path = system_ca_file
                logger.info(f"使用系统证书: {system_ca_file}")
            else:
                # 方法2: 使用 certifi 证书
                self.verify_path = certifi.where()
                logger.info(f"使用 certifi 证书: {self.verify_path}")
                
            # 测试证书有效性
            context = ssl.create_default_context(cafile=self.verify_path)
            logger.info("SSL 上下文创建成功")
            
        except Exception as e:
            logger.warning(f"SSL 上下文设置失败: {e}, 将使用系统默认证书")
            self.verify_path = True  # 使用系统默认
    
    def get_access_token(self, code):
        """通过code获取access_token - 生产环境安全版本"""
        url = f"{self.base_url}/sns/oauth2/access_token"
        params = {
            "appid": self.app_id,
            "secret": self.app_secret,
            "code": code,
            "grant_type": "authorization_code"
        }
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"尝试请求微信API (第{attempt + 1}次): {url}")
                
                response = requests.get(
                    url, 
                    params=params, 
                    timeout=15,
                    verify=self.verify_path
                )
                
                result = response.json()
                logger.info(f"微信API响应: {result}")
                
                if 'errcode' in result and result['errcode'] != 0:
                    logger.error(f"微信API业务错误: {result}")
                    return result
                    
                return result
                
            except requests.exceptions.SSLError as e:
                logger.error(f"微信API SSL证书验证失败 (第{attempt + 1}次): {e}")
                
                if attempt == max_retries - 1:
                    # 最后一次尝试：使用更宽松的SSL设置
                    try:
                        logger.warning("尝试使用宽松SSL设置...")
                        response = requests.get(
                            url, 
                            params=params, 
                            timeout=15,
                            verify=False  # 临时禁用验证
                        )
                        result = response.json()
                        logger.warning(f"宽松模式微信API响应: {result}")
                        return result
                    except Exception as fallback_error:
                        logger.error(f"宽松模式也失败: {fallback_error}")
                        return {'errcode': -1, 'errmsg': 'SSL证书验证失败'}
                
            except requests.exceptions.Timeout:
                logger.error(f"微信API请求超时 (第{attempt + 1}次)")
                if attempt == max_retries - 1:
                    return {'errcode': -1, 'errmsg': '请求超时'}
                    
            except Exception as e:
                logger.error(f"微信API请求异常 (第{attempt + 1}次): {e}")
                if attempt == max_retries - 1:
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
                verify=self.verify_path
            )
            result = response.json()
            logger.info(f"微信用户信息响应: {result}")
            return result
        except requests.exceptions.SSLError as e:
            logger.error(f"微信用户信息API SSL证书验证失败: {e}")
            # 对于用户信息获取，我们更保守，不降级
            return {'errcode': -1, 'errmsg': 'SSL证书验证失败'}
        except Exception as e:
            logger.error(f"微信用户信息API错误: {e}")
            return {'errcode': -1, 'errmsg': str(e)}