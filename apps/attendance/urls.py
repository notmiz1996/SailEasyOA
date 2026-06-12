# apps/attendance/urls.py

"""
考勤管理路由

/api/v1/classes/{class_id}/attendance/
  ├── GET    /           → 考勤列表
  ├── POST   /           → 录入考勤
  └── PUT    /{aid}/     → 修改考勤
"""

from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path(
        'classes/<uuid:class_id>/attendance/',
        views.AttendanceListCreateView.as_view(),
        name='attendance-list-create',
    ),
    path(
        'classes/<uuid:class_id>/attendance/<uuid:attendance_id>/',
        views.AttendanceUpdateView.as_view(),
        name='attendance-update',
    ),
]