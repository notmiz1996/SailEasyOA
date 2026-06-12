# apps/persons/admin.py

"""
Person + Region 的 Admin 配置
- Region：按 code 排序，支持按 level 筛选
- Person：支持按身份证号搜索、按省市区筛选
"""

from django.contrib import admin
from .models import Person, Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    """行政区划后台管理"""

    list_display = ('code', 'name', 'level', 'parent')
    list_filter = ('level',)
    search_fields = ('name', 'code')
    ordering = ('code',)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    """人员档案后台管理"""

    list_display = ('name', 'id_card', 'gender', 'phone', 'province', 'created_at')
    list_filter = ('gender', 'province')
    search_fields = ('name', 'id_card', 'phone')
    ordering = ('-created_at',)

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'id_card', 'gender', 'birth_date', 'phone', 'email')
        }),
        ('地址信息', {
            'fields': ('province', 'city', 'district', 'address_detail')
        }),
        ('紧急联系人', {
            'fields': ('emergency_contact', 'emergency_phone')
        }),
        ('微信绑定', {
            'fields': ('openid',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')