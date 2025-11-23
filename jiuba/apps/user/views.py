# user/views.py
import json
import random
import string
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import login, logout
from django.db import transaction
from .models import User
from .serializers import UserSerializer, UserRegistrationSerializer, UserLoginSerializer, UserBalancePointsSerializer
from .permissions import IsAdminUser
import logging

# 添加 CSRF 豁免
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action in ['register', 'login', 'wechat_smart_login']:
            return [AllowAny()]
        elif self.action in ['update_balance_points', 'user_list']:
            return [IsAuthenticated(), IsAdminUser]
        return [IsAuthenticated()]
    
    def _generate_username(self, nickname, phone_number):
        """生成用户名"""
        if nickname:
            # 清理昵称中的特殊字符
            base_username = ''.join(c for c in nickname.strip() if c.isalnum() or c in ['_', '-'])
            if not base_username:
                base_username = f"user{phone_number[-4:]}" if phone_number else "user"
        else:
            base_username = f"user{phone_number[-4:]}" if phone_number else "user"
        
        username = base_username
        counter = 1
        
        # 确保用户名唯一
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
            if counter > 100:
                random_suffix = ''.join(random.choices(string.digits, k=4))
                username = f"{base_username}{random_suffix}"
                break
        
        return username
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """用户注册"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': '注册成功',
                'user_id': user.id,
                'username': user.username
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """用户登录"""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            return Response({
                'message': '登录成功',
                'session_id': request.session.session_key,
                'user_id': user.id,
                'username': user.username
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def wechat_smart_login(self, request):
        """
        微信智能登录 - 强制要求手机号
        """
        encrypted_data = request.data.get('encrypted_data')
        iv = request.data.get('iv')
        code = request.data.get('code')
        user_info = request.data.get('user_info', {})
        
        logger.info(f"📱 收到微信登录请求: code={code}, encrypted_data长度={len(encrypted_data) if encrypted_data else 0}")
        
        # 强制要求手机号加密数据
        if not encrypted_data or not iv:
            logger.error("❌ 缺少手机号授权数据")
            return Response(
                {'error': '缺少手机号授权数据，请先授权手机号'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 强制要求微信 code
        if not code:
            logger.error("❌ 缺少微信授权code")
            return Response(
                {'error': '缺少微信授权code'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            try:
                # 1. 使用 code 获取 session_key
                logger.info("🔑 开始获取session_info")
                session_info = self.get_session_info_by_code(code)
                
                if not session_info or 'session_key' not in session_info:
                    logger.error("❌ 获取session_info失败")
                    return Response(
                        {'error': '微信授权失败'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                session_key = session_info['session_key']
                openid = session_info.get('openid')
                logger.info(f"✅ 成功获取 session_key 和 openid: {openid}")
                
                # 2. 直接使用原生方法解密手机号（wechatpy有问题）
                logger.info("🔐 开始解密手机号")
                phone_number = self.decrypt_phone_number_native(encrypted_data, iv, session_key)
                
                if not phone_number:
                    logger.error("❌ 手机号解密失败")
                    return Response(
                        {'error': '手机号解密失败'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                logger.info(f"✅ 成功解密手机号: {phone_number}")
                
                # 3. 验证手机号格式
                if not self.validate_phone_format(phone_number):
                    logger.error(f"❌ 手机号格式不正确: {phone_number}")
                    return Response(
                        {'error': '手机号格式不正确'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                user = None
                is_new_user = False
                
                # 4. 优先使用手机号识别用户
                if phone_number:
                    try:
                        user = User.objects.select_for_update().get(phone=phone_number)
                        logger.info(f"✅ 通过手机号找到用户: {user.username} (ID: {user.id})")
                        # 如果找到用户，绑定微信OpenID（如果还没有）
                        if openid and not user.wechat_openid:
                            user.wechat_openid = openid
                            user.save()
                            logger.info("🔗 绑定微信OpenID到现有用户")
                    except User.DoesNotExist:
                        logger.info("📞 手机号不存在，继续尝试OpenID")
                        pass
                
                # 5. 使用OpenID识别（备用方案）
                if not user and openid:
                    try:
                        user = User.objects.select_for_update().get(wechat_openid=openid)
                        logger.info(f"✅ 通过OpenID找到用户: {user.username} (ID: {user.id})")
                        # 如果通过OpenID找到用户，更新手机号
                        if phone_number and not user.phone:
                            user.phone = phone_number
                            user.save()
                            logger.info("📱 更新手机号到现有用户")
                    except User.DoesNotExist:
                        logger.info("🆕 OpenID也不存在，需要创建新用户")
                        pass
                
                # 6. 创建新用户
                if not user:
                    username = self._generate_username(
                        user_info.get('nickname'), 
                        phone_number
                    )
                    
                    # 创建用户时设置必填字段
                    user_data = {
                        'username': username,
                        'phone': phone_number,
                        'wechat_openid': openid,
                    }
                    
                    # 可选字段
                    if user_info.get('email'):
                        user_data['email'] = user_info.get('email')
                    
                    # 设置默认密码（微信登录用户不需要密码，但Django要求）
                    user_data['password'] = 'wechat_login_' + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                    
                    logger.info(f"🆕 创建用户数据: {user_data}")
                    
                    # 使用 create_user 方法创建用户（会处理密码加密）
                    user = User.objects.create_user(**user_data)
                    is_new_user = True
                    logger.info(f"🎉 创建新用户成功: {username} (ID: {user.id})")
                
                # 7. 登录用户
                login(request, user)
                logger.info(f"✅ 用户登录成功: {user.username} (ID: {user.id})")
                
                # 8. 立即从数据库重新加载用户信息，确保数据已保存
                user.refresh_from_db()
                logger.info(f"💾 数据库用户信息: 用户名={user.username}, 手机={user.phone}, OpenID={user.wechat_openid}")
                
                return Response({
                    'message': '登录成功',
                    'user_id': user.id,
                    'username': user.username,
                    'is_new_user': is_new_user,
                    'has_phone': bool(user.phone),
                    'has_wechat_bind': bool(user.wechat_openid),
                    'session_id': request.session.session_key
                })
                
            except Exception as e:
                logger.error(f"❌ 微信智能登录失败: {e}", exc_info=True)
                return Response(
                    {'error': '登录失败，请重试'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

    def get_session_info_by_code(self, code):
        """通过code获取session_key和openid"""
        try:
            import requests
            import urllib3
            # 禁用SSL警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            url = "https://api.weixin.qq.com/sns/jscode2session"
            params = {
                'appid': settings.WECHAT_APP_ID,
                'secret': settings.WECHAT_APP_SECRET,
                'js_code': code,
                'grant_type': 'authorization_code'
            }
            
            logger.info(f"🌐 调用微信API: appid={settings.WECHAT_APP_ID}")
            
            response = requests.get(url, params=params, verify=False, timeout=10)
            data = response.json()
            
            logger.info(f"📨 微信API响应: {data}")
            
            if 'session_key' in data and 'openid' in data:
                logger.info(f"✅ 成功获取session_info: openid={data['openid']}")
                return {
                    'session_key': data['session_key'],
                    'openid': data['openid']
                }
            else:
                logger.error(f"❌ 获取session_info失败: {data}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 获取session_info异常: {e}")
            return None

    def decrypt_phone_number_native(self, encrypted_data, iv, session_key):
        """
        使用原生方法解密微信手机号
        """
        try:
            import base64
            import json
            
            logger.info("🔐 开始解密手机号(原生方法)...")
            
            # Base64解码
            encrypted_data_bytes = base64.b64decode(encrypted_data)
            iv_bytes = base64.b64decode(iv)
            session_key_bytes = base64.b64decode(session_key)
            
            logger.info(f"📊 解码后长度 - encrypted_data: {len(encrypted_data_bytes)}, iv: {len(iv_bytes)}, session_key: {len(session_key_bytes)}")
            
            # 使用 pycryptodome 进行 AES 解密
            try:
                from Crypto.Cipher import AES
            except ImportError:
                logger.error("❌ 未安装pycryptodome")
                return None
            
            # AES解密
            cipher = AES.new(session_key_bytes, AES.MODE_CBC, iv_bytes)
            decrypted_bytes = cipher.decrypt(encrypted_data_bytes)
            
            # 去除PKCS7填充
            pad = decrypted_bytes[-1]
            if pad < 1 or pad > 32:
                pad = 0
            decrypted_bytes = decrypted_bytes[:-pad]
            
            logger.info(f"✅ 解密成功，字节长度: {len(decrypted_bytes)}")
            
            # 解析JSON
            decrypted_str = decrypted_bytes.decode('utf-8')
            logger.info(f"📄 解密后的数据: {decrypted_str}")
            
            phone_info = json.loads(decrypted_str)
            logger.info(f"📋 手机号信息: {phone_info}")
            
            # 提取手机号 - 尝试多个可能的字段名
            phone_number = phone_info.get('phoneNumber') or phone_info.get('purePhoneNumber')
            if phone_number:
                logger.info(f"✅ 成功解密手机号: {phone_number}")
                return phone_number
            else:
                logger.error(f"❌ 未找到手机号字段，完整数据: {phone_info}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 原生解密失败: {e}", exc_info=True)
            return None

    def validate_phone_format(self, phone):
        """验证手机号格式"""
        import re
        phone_pattern = re.compile(r'^1[3-9]\d{9}$')
        return bool(phone_pattern.match(phone))
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """用户登出"""
        logout(request)
        return Response({'message': '登出成功'})
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """获取当前用户信息"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def user_list(self, request):
        """
        获取用户列表（商家和管理员专用）
        用于在后台选择用户修改积分和余额
        """
        queryset = User.objects.all().order_by('-date_joined')
        
        # 搜索功能
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                username__icontains=search
            ) | queryset.filter(
                phone__icontains=search
            ) | queryset.filter(
                email__icontains=search
            )
        
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def update_balance_points(self, request, pk=None):
        """
        修改用户余额和积分（商家和管理员专用）
        """
        user = self.get_object()
        serializer = UserBalancePointsSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            # 记录修改日志
            old_balance = user.balance
            old_points = user.points
            new_balance = serializer.validated_data.get('balance', old_balance)
            new_points = serializer.validated_data.get('points', old_points)
            
            serializer.save()
            
            return Response({
                'message': '修改成功',
                'user_id': user.id,
                'username': user.username,
                'old_balance': float(old_balance),
                'new_balance': float(new_balance),
                'old_points': float(old_points),
                'new_points': float(new_points),
                'balance_change': float(new_balance - old_balance),
                'points_change': float(new_points - old_points)
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_balance(self, request, pk=None):
        """
        增加用户余额（商家和管理员专用）
        """
        user = self.get_object()
        amount = request.data.get('amount', 0)
        
        try:
            amount = float(amount)
            if amount <= 0:
                return Response(
                    {'error': '金额必须大于0'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': '金额格式错误'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_balance = user.balance
        user.balance += amount
        user.save()
        
        return Response({
            'message': '余额增加成功',
            'user_id': user.id,
            'username': user.username,
            'amount': amount,
            'old_balance': float(old_balance),
            'new_balance': float(user.balance)
        })
    
    @action(detail=True, methods=['post'])
    def add_points(self, request, pk=None):
        """
        增加用户积分（商家和管理员专用）
        """
        user = self.get_object()
        points = request.data.get('points', 0)
        
        try:
            points = int(points)
            if points <= 0:
                return Response(
                    {'error': '积分必须大于0'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': '积分格式错误'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_points = user.points
        user.points += points
        user.save()
        
        return Response({
            'message': '积分增加成功',
            'user_id': user.id,
            'username': user.username,
            'points': points,
            'old_points': old_points,
            'new_points': user.points
        })