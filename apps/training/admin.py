# apps/training/admin.py

"""
培训班级 Admin 配置
含 Post/Position 基础数据管理
"""

from django.contrib import admin
from .models import TrainingClass, CourseSchedule, ClassStatusTransition, ClassStatusRule, Post, Position


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """培训岗位后台管理"""
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')
    ordering = ('code',)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    """培训职务后台管理"""
    list_display = ('name', 'code', 'post', 'created_at')
    list_filter = ('post',)
    search_fields = ('name', 'code', 'post__name')
    ordering = ('post__code', 'code')


@admin.register(TrainingClass)
class TrainingClassAdmin(admin.ModelAdmin):
    """培训班级后台管理"""
    list_display = ('name', 'position', 'status', 'expected_start_date', 'actual_start_date', 'created_by', 'created_at')
    list_filter = ('status', 'position__post')
    search_fields = ('name', 'position__name')
    ordering = ('-created_at',)
    readonly_fields = ('actual_start_date', 'created_at', 'updated_at')


@admin.register(CourseSchedule)
class CourseScheduleAdmin(admin.ModelAdmin):
    """课程安排后台管理"""
    list_display = ('training_class', 'schedule_date', 'time_slot', 'course_name', 'course_type', 'instructor')
    list_filter = ('course_type', 'time_slot')
    search_fields = ('course_name', 'training_class__name')
    ordering = ('-schedule_date',)


@admin.register(ClassStatusTransition)
class ClassStatusTransitionAdmin(admin.ModelAdmin):
    """状态变更日志（只读）"""
    list_display = ('training_class', 'from_status', 'to_status', 'operator', 'operated_at')
    list_filter = ('from_status', 'to_status')
    ordering = ('-operated_at',)
    readonly_fields = ('training_class', 'from_status', 'to_status', 'operator', 'operated_at')
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClassStatusRule)
class ClassStatusRuleAdmin(admin.ModelAdmin):
    """状态转换规则配置"""
    list_display = ('from_status', 'to_status', 'allowed_role', 'precondition', 'is_reversible')
    list_filter = ('allowed_role', 'precondition', 'is_reversible')
    ordering = ('from_status', 'to_status')