# config/settings/base.py

"""
Django 公共配置
所有环境共用的配置项：INSTALLED_APPS、MIDDLEWARE、DRF、Django-Q、loguru
"""

import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------- 安全配置 ----------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-key-change-in-production'
)
DEBUG = True  # 各环境覆盖
ALLOWED_HOSTS = []

# ---------- App 注册 ----------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# 外部模块
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_q',  # Django-Q ORM Broker 无需额外部署
]

# 本地APP
LOCAL_APPS = [
    'apps.accounts',
    'apps.persons',
    'apps.training',
    'apps.enrollment',
    'apps.attendance',
    'apps.leave',
    'apps.notification',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------- 中间件 ----------
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ---------- 数据库 （各环境覆盖）----------
DATABASES = {}

# ---------- 密码校验 ----------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------- 国际化 ----------
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# ---------- 静态/媒体文件 ----------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'static'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 自定义用户模型
AUTH_USER_MODEL = 'accounts.User'

# ---------- Django REST Framework ----------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # 自定义分页类
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.StandardCursorPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'utils.exceptions.custom_exception_handler',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
}

# ---------- SimpleJWT ----------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=120),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ---------- Django-Q （ORM Broker，无需额外部署 Redis broker）----------
# ORM broker 模式下任务串行处理，poll=2 表示每 2 秒轮询一次数据库
# 如未来需更高吞吐量，可切换为 Redis broker
Q_CLUSTER = {
    'name': 'saileasy_oa',
    'broker': 'orm',            # 使用数据库作为 broker
    'timeout': 300,             # 任务超时 5 分钟（对齐批量导入场景）
    'retry': 360,               # 失败后 6 分钟重试
    'max_attempts': 3,          # 最多重试 3 次
    'poll': 2,                  # ORM broker 每 2 秒轮询一次
    'save_limit': 100,          # 保留最近 100 条成功任务记录
    'catch_up': False,          # cron 不追赶（错过不补跑）
    'schedule': [
        {
            'func': 'apps.notification.tasks.check_pending_leave_timeout',
            'schedule_type': 'H',   # 每小时执行
            'minutes': 0,
        },
    ],
}

# ---------- CORS ----------
CORS_ALLOW_ALL_ORIGINS = True  # 开发阶段放开，生产环境需配置白名单