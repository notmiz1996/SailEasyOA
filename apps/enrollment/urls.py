# apps/enrollment/urls.py

"""
学员报名模块路由

/api/v1/classes/{class_id}/enrollments/
  ├── GET    /                       → 报名列表
  ├── POST   /                       → 单条代录
  └── POST   /import/                → 批量导入（Excel）

注：嵌套在 training 的 classes/ 路径下
"""

from django.urls import path
from . import views

app_name = 'enrollment'

urlpatterns = [
    path('classes/<uuid:class_id>/enrollments/', views.EnrollmentListCreateView.as_view(), name='enrollment-list'),
    path('classes/<uuid:class_id>/enrollments/import/', views.EnrollmentImportView.as_view(), name='enrollment-import'),
    path('classes/<uuid:class_id>/enrollments/<uuid:enrollment_id>/check-in/', views.CheckInView.as_view(), name='enrollment-check-in'),
    path('classes/<uuid:class_id>/enrollments/batch-check-in/', views.BatchCheckInView.as_view(), name='enrollment-batch-check-in'),
]