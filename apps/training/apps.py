# apps/training/apps.py

"""
training 应用的 Django AppConfig
"""

from django.apps import AppConfig


class TrainingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.training'
    verbose_name = '培训班级'