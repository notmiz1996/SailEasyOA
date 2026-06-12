# apps/attendance/views.py

"""
考勤管理 API 视图

T-08（考勤管理）：
  GET   /api/v1/classes/{id}/attendance/         → 考勤列表（按班级查询）
  POST  /api/v1/classes/{id}/attendance/         → 录入考勤（半天维度）
  PUT   /api/v1/classes/{id}/attendance/{aid}/   → 修改考勤记录

权限设计（参考技术方案书 6.1 节）：
  录入/修改 → IsAuthenticated + (IsTeachingAdmin | IsTeacher)
  查询      → IsAuthenticated + (IsTeachingAdmin | IsTeacher)
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.training.models import TrainingClass
from apps.accounts.permissions import IsTeachingAdmin, IsTeacher
from .models import AttendanceRecord
from .serializers import (
    AttendanceCreateSerializer,
    AttendanceUpdateSerializer,
    AttendanceListSerializer,
)


class IsAttendanceManager(IsAuthenticated):
    """教学管理员或教学人员可以管理考勤"""
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return (
            IsTeachingAdmin().has_permission(request, view)
            or IsTeacher().has_permission(request, view)
        )


class AttendanceListCreateView(generics.GenericAPIView):
    """
    考勤列表 / 录入

    GET  /api/v1/classes/{class_id}/attendance/   → 考勤列表
    POST /api/v1/classes/{class_id}/attendance/   → 录入考勤

    GET 支持按 enrollment_id 筛选：?enrollment_id=xxx
    """
    permission_classes = [IsAuthenticated, IsAttendanceManager]

    def get_queryset(self):
        qs = AttendanceRecord.objects.filter(
            training_class_id=self.kwargs['class_id'],
        ).select_related(
            'enrollment__person',
        ).order_by('record_date', 'time_slot')

        enrollment_id = self.request.query_params.get('enrollment_id')
        if enrollment_id:
            qs = qs.filter(enrollment_id=enrollment_id)

        return qs

    def get(self, request, class_id):
        get_object_or_404(TrainingClass, pk=class_id)
        queryset = self.get_queryset()
        serializer = AttendanceListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, class_id):
        get_object_or_404(TrainingClass, pk=class_id)

        serializer = AttendanceCreateSerializer(
            data=request.data,
            context={
                'class_id': class_id,
                'created_by': request.user,
            },
        )
        serializer.is_valid(raise_exception=True)
        record = serializer.save()

        result_serializer = AttendanceListSerializer(record)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)


class AttendanceUpdateView(generics.GenericAPIView):
    """
    修改考勤记录

    PUT /api/v1/classes/{class_id}/attendance/{attendance_id}/
    """
    permission_classes = [IsAuthenticated, IsAttendanceManager]

    def put(self, request, class_id, attendance_id):
        get_object_or_404(TrainingClass, pk=class_id)

        record = get_object_or_404(
            AttendanceRecord, pk=attendance_id, training_class_id=class_id,
        )

        serializer = AttendanceUpdateSerializer(
            record, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated_record = serializer.save()

        result_serializer = AttendanceListSerializer(updated_record)
        return Response(result_serializer.data, status=status.HTTP_200_OK)