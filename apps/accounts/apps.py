# apps/accounts/apps.py

"""
accounts 应用的 Django AppConfig
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = '用户认证'