# apps/enrollment/apps.py

"""
enrollment 应用的 Django AppConfig
"""

from django.apps import AppConfig


class EnrollmentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.enrollment'
    verbose_name = '学员报名'