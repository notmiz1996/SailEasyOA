# apps/training/views.py

"""
培训班级 API 视图（技术方案书 v1.7，position FK 替换 training_type）

班级相关：
  GET    /api/v1/classes/            → 班级列表（支持 status 筛选）
  POST   /api/v1/classes/            → 创建班级
  GET    /api/v1/classes/{id}/       → 班级详情（含课程安排 + position 信息）
  PUT    /api/v1/classes/{id}/       → 编辑班级基础信息
  GET    /api/v1/classes/{id}/status/ → 获取可用状态转换列表
  POST   /api/v1/classes/{id}/status/ → 切换班级状态（幂等）

课程安排相关：
  GET    /api/v1/classes/{id}/courses/    → 课程列表
  POST   /api/v1/classes/{id}/courses/    → 添加课程
  DELETE /api/v1/classes/{id}/courses/{cid}/ → 删除课程

权限设计（参考技术方案书 6.1 节）：
  创建/编辑/状态切换 → IsTeachingAdmin
  课程管理           → IsTeachingAdmin
  列表/详情          → IsAuthenticated
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from .models import TrainingClass, CourseSchedule
from .enums import ClassStatus
from .serializers import (
    TrainingClassListSerializer,
    TrainingClassDetailSerializer,
    TrainingClassCreateSerializer,
    TrainingClassUpdateSerializer,
    CourseScheduleSerializer,
    StatusTransitionRequestSerializer,
    ClassStatusRuleSerializer,
)
from .services import ClassStatusService
from apps.accounts.permissions import IsTeachingAdmin


# ===================== 班级 =====================


class ClassListCreateView(generics.ListCreateAPIView):
    """
    班级列表 / 创建
    GET  /api/v1/classes/?status=ENROLLING  按状态筛选
    POST /api/v1/classes/                   创建班级（自动设为 DRAFT）
    权限：列表需要认证，创建需要 ADMIN 角色
    """

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return TrainingClassListSerializer
        return TrainingClassCreateSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsTeachingAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = TrainingClass.objects.select_related(
            'created_by', 'position', 'position__post',
        ).all()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs


class ClassRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    班级详情 / 编辑
    GET  /api/v1/classes/{id}/   详情（含课程安排列表 + position 信息）
    PUT  /api/v1/classes/{id}/   编辑基础信息
    """

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return TrainingClassDetailSerializer
        return TrainingClassUpdateSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsAuthenticated(), IsTeachingAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return TrainingClass.objects.select_related(
            'created_by', 'position', 'position__post',
        ).all()


class ClassStatusTransitionView(generics.GenericAPIView):
    """
    切换班级状态
    GET  /api/v1/classes/{id}/status/   获取允许转换的列表（前端渲染按钮用）
    POST /api/v1/classes/{id}/status/   执行状态切换
    { "to_status": "APPROVED", "remark": "审批通过" }
    幂等：已是目标状态重复调用返回 200（不报错）
    """

    serializer_class = StatusTransitionRequestSerializer
    permission_classes = [IsAuthenticated, IsTeachingAdmin]

    def post(self, request, *args, **kwargs):
        training_class = get_object_or_404(TrainingClass, pk=kwargs['pk'])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ClassStatusService()
        try:
            result = service.transition(
                class_id=str(training_class.id),
                target_status=serializer.validated_data['to_status'],
                operator=request.user,
                remark=serializer.validated_data.get('remark', ''),
            )
        except ValidationError as e:
            return Response(
                {'code': 'E-CLS-01', 'message': str(e), 'data': None},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(result, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        """GET 获取当前状态允许的转换列表"""
        training_class = get_object_or_404(TrainingClass, pk=kwargs['pk'])
        service = ClassStatusService()
        available = service.get_available_transitions(training_class)
        return Response({
            'current_status': training_class.status,
            'current_status_display': training_class.get_status_display(),
            'available_transitions': available,
        })


# ===================== 课程安排 =====================


class CourseScheduleListCreateView(generics.ListCreateAPIView):
    """
    课程安排列表 / 添加
    GET  /api/v1/classes/{class_id}/courses/   → 课程列表
    POST /api/v1/classes/{class_id}/courses/   → 添加课程
    """

    serializer_class = CourseScheduleSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsTeachingAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return CourseSchedule.objects.filter(
            training_class_id=self.kwargs['class_id'],
        ).select_related('training_class', 'instructor')

    def perform_create(self, serializer):
        training_class = get_object_or_404(TrainingClass, pk=self.kwargs['class_id'])

        # 检查班级是否已归档（WBS T-04 验收标准 #3）
        if training_class.status == ClassStatus.ARCHIVED:
            raise ValidationError('已归档的班级不可修改课程安排')

        serializer.save(training_class=training_class)


class CourseScheduleDestroyView(generics.DestroyAPIView):
    """
    删除课程安排
    DELETE /api/v1/classes/{class_id}/courses/{pk}/
    """

    permission_classes = [IsAuthenticated, IsTeachingAdmin]

    def get_object(self):
        course = get_object_or_404(
            CourseSchedule,
            pk=self.kwargs['pk'],
            training_class_id=self.kwargs['class_id'],
        )

        # 检查班级是否已归档
        if course.training_class.status == ClassStatus.ARCHIVED:
            raise ValidationError('已归档的班级不可修改课程安排')

        return course