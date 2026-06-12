# config/settings/dev.py

"""
开发环境配置
SQLite 数据库 + DEBUG=True + 详细日志
"""

from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# SQLite 开发数据库
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 开发环境不强制 HTTPS
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# 开发日志级别 DEBUG
LOG_LEVEL = 'DEBUG'