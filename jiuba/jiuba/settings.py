"""
Django settings for jiuba project.
"""

import sys
import os
from pathlib import Path
import pymysql
pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent

# 从环境变量获取配置，避免硬编码
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-7wvs^r**wk+jh(#8o&owtno2y%jafm-@0o5sngrh0nw1*jd_6^')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

# 添加 CSRF 配置
CSRF_TRUSTED_ORIGINS = [
    'https://jiuba-houduan2-prod-6gjjc9fif161add1-1384962309.ap-shanghai.run.wxcloudrun.com',
    'http://jiuba-houduan2-prod-6gjjc9fif161add1-1384962309.ap-shanghai.run.wxcloudrun.com',
    'https://django-98-198339-5-1386025783.sh.run.tcloudbase.com',
    'https://*.run.tcloudbase.com',
    'http://*.run.tcloudbase.com',
]

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
FILE_UPLOAD_PERMISSIONS = 0o644

# 自定义用户模型
AUTH_USER_MODEL = 'user.User'

# 将apps目录添加到Python路径中
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders', 
    'django_filters',
    'apps.product',
    'apps.order',
    'apps.user',
    'apps.reservations',
    'apps.payment',  # 新增支付应用
    'apps.shop',
    'apps.endpoints',
    'apps.services',
    'apps.cart',
    'apps.activity',
    'apps.merchant',
    'apps.notice',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'jiuba.middleware.MerchantAuthMiddleware',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
ROOT_URLCONF = 'jiuba.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'apps/merchant/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.debug',
            ],
        },
    },
]

WSGI_APPLICATION = 'jiuba.wsgi.application'

# 数据库配置 - 使用微信云托管的MySQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('MYSQL_DATABASE', 'jiuba'),
        'USER': os.environ.get('MYSQL_USERNAME', 'root'),
        'PASSWORD': os.environ.get('MYSQL_PASSWORD', 'Yx741520'),
        'HOST': os.environ.get('MYSQL_HOST', '10.29.104.89'),
        'PORT': os.environ.get('MYSQL_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

# 添加详细的数据库连接测试
try:
    from django.db import connections
    conn = connections['default']
    conn.cursor()
    print("✅ 数据库连接成功")
except Exception as e:
    print(f"❌ 数据库连接失败: {e}")

# 如果找不到MySQL配置，回退到SQLite（仅用于开发）
if os.environ.get('MYSQL_HOST') is None and DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3', 
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# 静态文件设置
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

CORS_ALLOW_ALL_ORIGINS = True

# ============================================================================
# 微信云托管支付配置（完整版）
# ============================================================================

# 小程序配置
WECHAT_APP_ID = os.environ.get('WECHAT_APP_ID', 'wxe3c395b43b7f1459')
WECHAT_APP_SECRET = os.environ.get('WECHAT_APP_SECRET', '39cec0936af3996ac806a548fca25442')

# 微信支付商户配置（必需）
WECHAT_MERCHANT_ID = os.environ.get('WECHAT_MERCHANT_ID', '')
WECHAT_MERCHANT_KEY = os.environ.get('WECHAT_MERCHANT_KEY', '')

# 微信云托管环境配置（必需）
WECHAT_CLOUD_ENV_ID = os.environ.get('WECHAT_CLOUD_ENV_ID', '')
WECHAT_CLOUD_SERVICE = os.environ.get('WECHAT_CLOUD_SERVICE', 'django-98')  # 你的服务名称

# 站点URL（用于回调）
SITE_URL = os.environ.get('SITE_URL', 'https://django-98-198339-5-1386025783.sh.run.tcloudbase.com')

# 支付回调URL
WECHAT_NOTIFY_URL = f'{SITE_URL}/api/payment/wechat/callback/'

# 打印配置检查
print("=" * 50)
print("微信支付配置检查:")
print(f"✅ WECHAT_APP_ID: {'已设置' if WECHAT_APP_ID else '未设置'}")
print(f"✅ WECHAT_MERCHANT_ID: {'已设置' if WECHAT_MERCHANT_ID else '未设置'}")
print(f"✅ WECHAT_CLOUD_ENV_ID: {'已设置' if WECHAT_CLOUD_ENV_ID else '未设置'}")
print(f"✅ WECHAT_CLOUD_SERVICE: {WECHAT_CLOUD_SERVICE}")
print(f"✅ SITE_URL: {SITE_URL}")
print(f"✅ 回调URL: {WECHAT_NOTIFY_URL}")
print("=" * 50)

# 检查必要配置
if not all([WECHAT_APP_ID, WECHAT_MERCHANT_ID, WECHAT_CLOUD_ENV_ID]):
    print("⚠️  警告: 微信支付必要配置缺失，支付功能将不可用")
    print("请在环境变量中设置:")
    print("  - WECHAT_APP_ID: 小程序AppID")
    print("  - WECHAT_MERCHANT_ID: 微信支付商户号")
    print("  - WECHAT_CLOUD_ENV_ID: 微信云托管环境ID")

# ============================================================================
# 日志配置
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'apps.payment': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.order': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# 确保logs目录存在
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# ============================================================================
# 安全配置（生产环境）
# ============================================================================

if not DEBUG:
    # 生产环境安全配置
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
    
    # 限制ALLOWED_HOSTS
    if 'ALLOWED_HOSTS' in os.environ:
        ALLOWED_HOSTS = os.environ['ALLOWED_HOSTS'].split(',')
    
    print("🔒 生产环境安全配置已启用")