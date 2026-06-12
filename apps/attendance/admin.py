# apps/attendance/admin.py

"""
考勤管理后台
"""

from django.contrib import admin

from .models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'training_class', 'record_date', 'time_slot', 'status', 'created_by')
    list_filter = ('status', 'time_slot', 'record_date')
    search_fields = ('enrollment__person__name', 'enrollment__person__id_card')
    ordering = ('-record_date', '-time_slot')
    readonly_fields = ('created_at', 'updated_at')