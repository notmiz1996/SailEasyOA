# config/urls.py

"""
项目根路由
/api/v1/ 前缀统一管理所有业务 API
admin/ 为 Django Admin 后台
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # 业务 API 统一前缀（T-02 起逐步挂载各 app 的路由）
    path('api/v1/auth/', include('apps.accounts.urls')),
    # T-03: 人员档案模块
    path('api/v1/', include('apps.persons.urls')),
    # T-04: 培训班级模块（含课程安排）
    path('api/v1/', include('apps.training.urls')),
    # T-05: 学员报名模块（代录 + 批量导入）
    path('api/v1/', include('apps.enrollment.urls')),
    # T-08: 考勤管理
    path('api/v1/', include('apps.attendance.urls')),
]