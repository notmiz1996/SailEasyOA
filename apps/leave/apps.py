# apps/leave/apps.py

"""
leave 应用的 Django AppConfig
"""

from django.apps import AppConfig


class LeaveConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.leave'
    verbose_name = '请假审批'