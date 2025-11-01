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
]

# 媒体文件配置 - 后续需要改为对象存储
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
    'apps.payment',
    'apps.shop',
    'apps.endpoints',
    'apps.services',
    'apps.cart',
    'apps.activity',
    'apps.merchant',
    'apps.notice',
    'apps.auth',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # 调整位置
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
        'HOST': os.environ.get('MYSQL_HOST', '10.14.105.205'),
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

# 微信配置从环境变量读取
WECHAT_APP_ID = os.environ.get('WECHAT_APP_ID', 'wx9710c346e5e1ddd7')
WECHAT_APP_SECRET = os.environ.get('WECHAT_APP_SECRET', '1f9818e5b1458dfc70cc41ef8cff0f56')
WECHAT_MCH_ID = os.environ.get('WECHAT_MCH_ID', '您的微信支付商户号')
WECHAT_API_KEY = os.environ.get('WECHAT_API_KEY', '您的微信支付API密钥')
WECHAT_NOTIFY_URL = os.environ.get('WECHAT_NOTIFY_URL', 'https://yourdomain.com/api/payment/wechat-callback/')
# 认证后端
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'apps.auth.backends.WeChatBackend',  # 微信登录后端
]