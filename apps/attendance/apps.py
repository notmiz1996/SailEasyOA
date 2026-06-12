# apps/attendance/apps.py

"""
attendance 应用的 Django AppConfig
"""

from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.attendance'
    verbose_name = '考勤管理'