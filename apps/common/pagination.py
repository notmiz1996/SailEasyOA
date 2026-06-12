# apps/common/pagination.py

"""
自定义分页类
统一使用 created_at 排序（项目所有模型均使用 created_at 字段名）
"""

from rest_framework.pagination import CursorPagination


class StandardCursorPagination(CursorPagination):
    """标准游标分页，使用 created_at 作为排序字段"""
    ordering = '-created_at'
    page_size = 20