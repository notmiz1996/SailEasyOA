# apps/training/urls.py

"""
培训班级模块路由（技术方案书 v1.7）

/api/v1/classes/
  ├── GET    /                       → 班级列表
  ├── POST   /                       → 创建班级
  ├── GET    /{id}/                  → 班级详情
  ├── PUT    /{id}/                  → 编辑班级
  ├── GET    /{id}/status/           → 可用状态切换列表
  ├── POST   /{id}/status/           → 切换状态（幂等）
  ├── GET    /{id}/courses/          → 课程列表
  ├── POST   /{id}/courses/          → 添加课程
  └── DELETE /{id}/courses/{cid}/    → 删除课程
"""

from django.urls import path
from . import views

app_name = 'training'

urlpatterns = [
    # 班级
    path('classes/', views.ClassListCreateView.as_view(), name='class-list'),
    path('classes/<uuid:pk>/', views.ClassRetrieveUpdateView.as_view(), name='class-detail'),
    path('classes/<uuid:pk>/status/', views.ClassStatusTransitionView.as_view(), name='class-status'),
    # 课程安排（嵌套路由）
    path('classes/<uuid:class_id>/courses/', views.CourseScheduleListCreateView.as_view(), name='course-list'),
    path('classes/<uuid:class_id>/courses/<uuid:pk>/', views.CourseScheduleDestroyView.as_view(), name='course-delete'),
]