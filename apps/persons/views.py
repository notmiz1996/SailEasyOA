# apps/persons/views.py

"""
Person 和 Region 的 API 视图

Person 相关：
  GET    /api/v1/persons/              → 人员列表（支持 id_card/phone/name 搜索）
  POST   /api/v1/persons/              → 创建人员档案
  GET    /api/v1/persons/{id}/         → 人员详情
  PUT    /api/v1/persons/{id}/         → 更新人员档案
  GET    /api/v1/persons/lookup/       → 按身份证号/手机号快速查找

Region 相关：
  GET    /api/v1/regions/              → 行政区划列表（支持 parent_id 筛选）
  GET    /api/v1/regions/provinces/    → 省份列表（快捷入口）
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Person, Region
from .serializers import (
    PersonReadSerializer,
    PersonWriteSerializer,
    PersonLookupSerializer,
    RegionSerializer,
    RegionListSerializer,
)


# ===================== Person 视图 =====================


class PersonListCreateView(generics.ListCreateAPIView):
    """
    人员列表 / 创建

    GET: 支持 q 参数搜索（同时匹配 name / id_card / phone）
         ?q=张三        → 姓名包含"张三"
         ?id_card=...   → 精确匹配身份证号
         ?phone=...     → 精确匹配手机号
    POST: 创建人员档案，身份证号自动提取性别和出生日期
    """

    queryset = Person.objects.select_related('province', 'city', 'district').all()

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return PersonReadSerializer
        return PersonWriteSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        # 精确查询优先级高：id_card > phone > q（模糊搜索）
        id_card = self.request.query_params.get('id_card')
        phone = self.request.query_params.get('phone')
        q = self.request.query_params.get('q')

        if id_card:
            qs = qs.filter(id_card=id_card)
        elif phone:
            qs = qs.filter(phone=phone)
        elif q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(id_card__icontains=q) |
                Q(phone__icontains=q)
            )

        return qs


class PersonRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    人员详情 / 更新
    PUT 时省市区传入 ID，身份证号变更会触发唯一性校验
    """

    queryset = Person.objects.select_related('province', 'city', 'district').all()

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return PersonReadSerializer
        return PersonWriteSerializer


class PersonLookupView(generics.GenericAPIView):
    """
    按身份证号或手机号快速查找已有档案
    用于报名时判断该学员是否已有 Person 记录

    GET /api/v1/persons/lookup/?id_card=440101199001011234
    → {"exists": true, "person": { ... }} 或 {"exists": false, "person": null}
    """

    serializer_class = PersonLookupSerializer

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        params = serializer.validated_data
        query = Q()
        if params.get('id_card'):
            query &= Q(id_card=params['id_card'])
        if params.get('phone'):
            query &= Q(phone=params['phone'])

        person = Person.objects.filter(query).select_related('province', 'city', 'district').first()

        if person:
            data = PersonReadSerializer(person).data
            return Response({'exists': True, 'person': data})
        return Response({'exists': False, 'person': None})


# ===================== Region 视图 =====================


class RegionListView(generics.ListAPIView):
    """
    行政区划列表
    支持 parent_id 筛选（用于省市区级联下拉）：
      parent_id 不传 → 返回所有省份（level=1）
      parent_id=44  → 返回广东省下属所有市
    """

    serializer_class = RegionListSerializer
    pagination_class = None  # 区域数据量小，不分页

    def get_queryset(self):
        parent_id = self.request.query_params.get('parent_id')
        if parent_id:
            return Region.objects.filter(parent_id=parent_id)
        # 默认返回所有省份
        return Region.objects.filter(level=1)


class ProvinceListView(generics.ListAPIView):
    """
    省份列表（快捷入口）
    GET /api/v1/regions/provinces/
    """

    serializer_class = RegionListSerializer
    queryset = Region.objects.filter(level=1)
    pagination_class = None