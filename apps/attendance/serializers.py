# apps/attendance/serializers.py

"""
考勤记录序列化器

- AttendanceCreateSerializer：录入考勤（含前置校验）
- AttendanceUpdateSerializer：修改考勤状态
- AttendanceListSerializer：考勤列表展示（含学员信息）
"""

from rest_framework import serializers
from django.db import IntegrityError

from .models import AttendanceRecord
from apps.enrollment.models import Enrollment


class AttendanceCreateSerializer(serializers.Serializer):
    """录入考勤"""
    enrollment_id = serializers.UUIDField(label='报名记录ID')
    record_date = serializers.DateField(label='考勤日期')
    time_slot = serializers.ChoiceField(
        choices=['morning', 'afternoon'], label='时段',
    )
    status = serializers.ChoiceField(
        choices=['present', 'absent', 'leave'], label='考勤状态',
        default='present',
    )

    def validate_enrollment_id(self, value):
        class_id = self.context.get('class_id')
        try:
            enrollment = Enrollment.objects.select_related('person').get(
                pk=value, training_class_id=class_id,
            )
        except Enrollment.DoesNotExist:
            raise serializers.ValidationError(
                '该报名记录不存在或不属于本班级', code='E-VALID-03',
            )

        if enrollment.enrollment_status != Enrollment.EnrollmentStatus.CHECKED_IN:
            raise serializers.ValidationError(
                '学员未报到，无法录入考勤', code='E-ENR-02',
            )

        self.context['_enrollment'] = enrollment
        return value

    def create(self, validated_data):
        enrollment = self.context['_enrollment']
        training_class_id = self.context['class_id']
        created_by = self.context.get('created_by')

        try:
            record = AttendanceRecord.objects.create(
                enrollment=enrollment,
                training_class_id=training_class_id,
                record_date=validated_data['record_date'],
                time_slot=validated_data['time_slot'],
                status=validated_data.get('status', 'present'),
                created_by=created_by,
            )
        except IntegrityError:
            raise serializers.ValidationError(
                '该学员此时段已有考勤记录，不可重复录入', code='E-ATT-01',
            )

        return record


class AttendanceUpdateSerializer(serializers.Serializer):
    """修改考勤"""
    status = serializers.ChoiceField(
        choices=['present', 'absent', 'leave'], label='考勤状态',
    )

    def update(self, instance, validated_data):
        instance.status = validated_data.get('status', instance.status)
        instance.save(update_fields=['status'])
        return instance


class AttendanceListSerializer(serializers.ModelSerializer):
    """考勤列表（含学员信息）"""
    enrollment_id = serializers.UUIDField(source='enrollment.id', read_only=True)
    person_name = serializers.CharField(source='enrollment.person.name', read_only=True)
    person_id_card = serializers.CharField(source='enrollment.person.id_card', read_only=True)
    time_slot_display = serializers.CharField(source='get_time_slot_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'enrollment_id', 'person_name', 'person_id_card',
            'record_date', 'time_slot', 'time_slot_display',
            'status', 'status_display', 'created_by',
            'created_at', 'updated_at',
        ]