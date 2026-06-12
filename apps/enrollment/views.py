# apps/enrollment/views.py

"""
学员报名 API 视图

报名相关（T-05）：
  GET  /api/v1/classes/{id}/enrollments/         → 报名列表（含学员信息）
  POST /api/v1/classes/{id}/enrollments/         → 单条代录（创建Person+Enrollment）

批量导入相关（T-06）：
  POST /api/v1/classes/{id}/enrollments/import/  → 上传Excel，启动异步导入

权限设计（参考技术方案书 6.1 节）：
  列表查看     → IsAuthenticated
  代录/导入    → IsTeachingAdmin
"""

import uuid
import tempfile
import os

from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated


from apps.training.models import TrainingClass
from apps.training.enums import ClassStatus, CHECKIN_ALLOWED_STATUSES
from apps.accounts.permissions import IsTeachingAdmin
from .models import Enrollment
from .serializers import (
    EnrollmentListSerializer,
    CreateEnrollmentSerializer,
    ImportResultSerializer,
)

from utils.logging import logger

from .tasks import import_enrollments_task


class EnrollmentListCreateView(generics.ListCreateAPIView):
    """
    报名列表 / 单条代录
    GET  /api/v1/classes/{class_id}/enrollments/   → 报名列表
    POST /api/v1/classes/{class_id}/enrollments/   → 代录学员

    权限：
    - GET: 需要认证
    - POST: 需要 ADMIN 角色
    """

    serializer_class = EnrollmentListSerializer

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return EnrollmentListSerializer
        return CreateEnrollmentSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsTeachingAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Enrollment.objects.filter(
            training_class_id=self.kwargs['class_id'],
        ).select_related('person', 'training_class').all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method == 'POST':
            training_class = get_object_or_404(
                TrainingClass, pk=self.kwargs['class_id'],
            )
            context['training_class'] = training_class
        return context

    def create(self, request, *args, **kwargs):
        training_class = get_object_or_404(
            TrainingClass, pk=self.kwargs['class_id'],
        )

        serializer = CreateEnrollmentSerializer(
            data=request.data,
            context={'training_class': training_class},
        )
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = serializer.save()
        except ValidationError as e:
            return Response(
                {'code': 'E-ENR-01', 'message': str(e), 'data': None},
                status=status.HTTP_409_CONFLICT,
            )

        result_serializer = EnrollmentListSerializer(enrollment)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)


class EnrollmentImportView(APIView):
    """
    批量导入（Excel）
    POST /api/v1/classes/{class_id}/enrollments/import/

    流程：
    1. 接收上传的 Excel 文件
    2. 保存到临时目录
    3. 启动 Django-Q 异步任务
    4. 返回 task_id（前端轮询结果）

    权限：仅教学管理员
    """

    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated, IsTeachingAdmin]

    def post(self, request, *args, **kwargs):
        training_class = get_object_or_404(
            TrainingClass, pk=self.kwargs['class_id'],
        )

        file = request.FILES.get('file')
        if not file:
            return Response(
                {'code': 'E-BAT-05', 'message': '请上传文件', 'data': None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ('.xlsx', '.xls'):
            return Response(
                {'code': 'E-BAT-06', 'message': '仅支持 .xlsx / .xls 格式', 'data': None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f'import_{uuid.uuid4().hex}{ext}')
        with open(temp_path, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)

        from django_q.tasks import async_task

        task_id = uuid.uuid4().hex
        async_task(
            'apps.enrollment.tasks.import_enrollments_task',
            str(training_class.id),
            temp_path,
            task_id=task_id,
        )

        return Response(
            {
                'task_id': task_id,
                'message': f'导入任务已提交，正在处理文件 [{file.name}]',
            },
            status=status.HTTP_202_ACCEPTED,
        )


# ============================================================
# T-07: 学员报到
# ============================================================

class CheckInView(APIView):
    """
    学员单个报到
    POST /api/v1/classes/{class_id}/enrollments/{enrollment_id}/check-in/

    幂等：已报到学员重复调用返回 200，不更新 checked_in_at。
    前置条件：班级状态需为 ENROLLING/ROSTER_GENERATED/SUBMITTED/PENDING_APPROVAL/APPROVED
    """
    permission_classes = [IsAuthenticated, IsTeachingAdmin]

    def post(self, request, class_id, enrollment_id):
        training_class = get_object_or_404(TrainingClass, pk=class_id)

        # 校验班级状态：报到仅允许在开班前的几个状态
        if training_class.status not in CHECKIN_ALLOWED_STATUSES:
            return Response(
                {'code': 'E-CLS-01', 'message': f'当前班级状态 [{training_class.status}] 不允许报到操作', 'data': None},
                status=status.HTTP_409_CONFLICT,
            )

        enrollment = get_object_or_404(
            Enrollment, pk=enrollment_id, training_class_id=class_id,
        )

        # 幂等处理：已是 CHECKED_IN 直接返回成功
        if enrollment.enrollment_status == Enrollment.EnrollmentStatus.CHECKED_IN:
            serializer = EnrollmentListSerializer(enrollment)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # 更新为已报到
        enrollment.enrollment_status = Enrollment.EnrollmentStatus.CHECKED_IN
        enrollment.checked_in_at = timezone.now()
        enrollment.save(update_fields=['enrollment_status', 'checked_in_at'])

        logger.info(
            f'报到确认：管理员 [{request.user.username}] '
            f'将学员 [{enrollment.person.name}] '
            f'在班级 [{training_class.name}] 标记为已报到'
        )

        serializer = EnrollmentListSerializer(enrollment)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BatchCheckInView(APIView):
    """
    批量报到
    POST /api/v1/classes/{class_id}/enrollments/batch-check-in/

    请求体：{"enrollment_ids": ["uuid1", "uuid2", ...]}
    已报到的学员自动忽略，不更新 checked_in_at。
    使用 select_for_update() 按 ID 顺序锁定，防止并发脏写。

    返回：{"success_count": N, "ignored_count": M, "failed_ids": [...]}
    """
    permission_classes = [IsAuthenticated, IsTeachingAdmin]

    def post(self, request, class_id):
        training_class = get_object_or_404(TrainingClass, pk=class_id)

        # 校验班级状态
        allowed_statuses = {
            'ENROLLING', 'ROSTER_GENERATED', 'SUBMITTED',
            'PENDING_APPROVAL', 'APPROVED',
        }
        if training_class.status not in allowed_statuses:
            return Response(
                {'code': 'E-CLS-01', 'message': f'当前班级状态 [{training_class.status}] 不允许报到操作', 'data': None},
                status=status.HTTP_409_CONFLICT,
            )

        enrollment_ids = request.data.get('enrollment_ids', [])
        if not enrollment_ids or not isinstance(enrollment_ids, list):
            return Response(
                {'code': 'E-VALID-03', 'message': '请提供 enrollment_ids 列表', 'data': None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 按 ID 排序后加行级锁，防止死锁
        sorted_ids = sorted(set(str(eid) for eid in enrollment_ids))

        enrollments = Enrollment.objects.filter(
            pk__in=sorted_ids,
            training_class_id=class_id,
        ).select_related('person').order_by('id').select_for_update()

        success_count = 0
        ignored_count = 0
        processed_ids = set()
        now = timezone.now()

        for enrollment in enrollments:
            processed_ids.add(str(enrollment.id))
            if enrollment.enrollment_status == Enrollment.EnrollmentStatus.CHECKED_IN:
                ignored_count += 1
                continue

            enrollment.enrollment_status = Enrollment.EnrollmentStatus.CHECKED_IN
            enrollment.checked_in_at = now
            enrollment.save(update_fields=['enrollment_status', 'checked_in_at'])
            success_count += 1

            logger.info(
                f'批量报到确认：管理员 [{request.user.username}] '
                f'将学员 [{enrollment.person.name}] '
                f'在班级 [{training_class.name}] 标记为已报到'
            )

        # 找出未找到的 ID（可能是无效 ID 或不属于本班级）
        not_found_ids = [eid for eid in sorted_ids if eid not in processed_ids]

        return Response({
            'success_count': success_count,
            'ignored_count': ignored_count,
            'failed_ids': not_found_ids,
        }, status=status.HTTP_200_OK)