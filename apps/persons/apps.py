# apps/persons/apps.py

"""
persons 应用的 Django AppConfig
"""

from django.apps import AppConfig


class PersonsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.persons'
    verbose_name = '人员档案'