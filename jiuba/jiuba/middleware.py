"""
中间件模块
"""
import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import redirect

logger = logging.getLogger(__name__)

class PaymentLoggingMiddleware(MiddlewareMixin):
    """
    支付请求日志中间件
    """
    
    def process_request(self, request):
        # 记录支付相关的请求
        if request.path.startswith('/api/payment/') or '/pay/' in request.path:
            try:
                if request.method in ['POST', 'PUT']:
                    # 安全地记录请求体（不记录敏感信息）
                    safe_body = {}
                    if request.body:
                        try:
                            body_data = json.loads(request.body.decode('utf-8'))
                            # 过滤敏感信息
                            if isinstance(body_data, dict):
                                for key in ['password', 'api_key', 'secret', 'key']:
                                    if key in body_data:
                                        body_data[key] = '***FILTERED***'
                            safe_body = body_data
                        except:
                            safe_body = {'raw_body': '[无法解析]'}
                    
                    logger.info(f"支付请求: {request.method} {request.path} - IP: {self.get_client_ip(request)} - Body: {json.dumps(safe_body)}")
            except Exception as e:
                logger.debug(f"记录支付请求日志失败: {str(e)}")
    
    def process_response(self, request, response):
        # 记录支付相关的响应
        if request.path.startswith('/api/payment/') or '/pay/' in request.path:
            try:
                if hasattr(response, 'data'):
                    # 过滤敏感信息
                    safe_data = response.data.copy() if hasattr(response.data, 'copy') else response.data
                    if isinstance(safe_data, dict):
                        for key in ['payment_config', 'paySign', 'package']:
                            if key in safe_data:
                                safe_data[key] = '***FILTERED***'
                    
                    logger.info(f"支付响应: {request.method} {request.path} - Status: {response.status_code} - Data: {json.dumps(safe_data)[:500]}...")
            except Exception as e:
                logger.debug(f"记录支付响应日志失败: {str(e)}")
        return response
    
    def get_client_ip(self, request):
        """获取客户端IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class MerchantAuthMiddleware(MiddlewareMixin):
    """
    商家权限中间件
    检查用户是否有权限访问商家后台
    """
    
    def process_request(self, request):
        # 只处理商家后台的请求
        if request.path.startswith('/merchant/'):
            # 排除登录页面
            if request.path == '/merchant/login/' or request.path == '/merchant/logout/':
                return None
            
            # 检查用户是否认证
            if not request.user.is_authenticated:
                return redirect(f'/merchant/login/?next={request.path}')
            
            # 检查用户是否是商家（is_staff表示商家）
            if not request.user.is_staff:
                # 如果不是商家，重定向到无权限页面或登录页面
                from django.contrib import messages
                from django.shortcuts import redirect
                messages.error(request, "您没有权限访问商家后台")
                return redirect('/merchant/login/')
        
        return None
    
    def process_response(self, request, response):
        return response

class ExceptionLoggingMiddleware(MiddlewareMixin):
    """
    异常日志中间件
    """
    
    def process_exception(self, request, exception):
        # 记录异常信息
        logger.error(f"请求异常: {request.method} {request.path}", exc_info=True)
        
        # 支付相关异常特别记录
        if '/payment/' in request.path or '/pay/' in request.path:
            logger.error(f"支付相关异常: {str(exception)}", exc_info=True)
        
        return None