# apps/enrollment/admin.py

"""
学员报名 Admin 配置
"""

from django.contrib import admin
from .models import Enrollment, ImportErrorLog


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """学员报名后台管理"""
    list_display = ('person', 'training_class', 'enrollment_status', 'enrolled_at', 'checked_in_at')
    list_filter = ('enrollment_status',)
    search_fields = ('person__name', 'person__id_card', 'training_class__name')
    ordering = ('-enrolled_at',)
    readonly_fields = ('enrolled_at', 'checked_in_at', 'created_at')


@admin.register(ImportErrorLog)
class ImportErrorLogAdmin(admin.ModelAdmin):
    """导入错误日志（只读）"""
    list_display = ('task_id', 'row_num', 'error_type', 'error_message', 'created_at')
    list_filter = ('error_type',)
    search_fields = ('task_id',)
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False