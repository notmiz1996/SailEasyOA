# apps/persons/urls.py

"""
人员档案模块路由

/api/v1/persons/
  ├── GET  /                   → 人员列表（支持搜索）
  ├── POST /                   → 创建人员档案
  ├── GET  /lookup/            → 按身份证/手机号快速查找
  └── GET|PUT /{id}/           → 详情 / 更新

/api/v1/regions/
  ├── GET  /                   → 行政区划列表（支持 parent_id 筛选）
  └── GET  /provinces/         → 省份列表（快捷入口）
"""

from django.urls import path
from . import views

app_name = 'persons'

urlpatterns = [
    # Person人员
    path('persons/', views.PersonListCreateView.as_view(), name='person-list'),
    path('persons/lookup/', views.PersonLookupView.as_view(), name='person-lookup'),
    path('persons/<uuid:pk>/', views.PersonRetrieveUpdateView.as_view(), name='person-detail'),
    # Region地址
    path('regions/', views.RegionListView.as_view(), name='region-list'),
    path('regions/provinces/', views.ProvinceListView.as_view(), name='region-provinces'),
]