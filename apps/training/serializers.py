# apps/training/serializers.py

"""
培训班级序列化器（技术方案书 v1.7，position FK 替换 training_type）

- TrainingClassListSerializer:       列表（精简字段）
- TrainingClassDetailSerializer:     详情（含课程表 + position 扩展信息）
- TrainingClassCreateSerializer:     创建
- TrainingClassUpdateSerializer:     更新
- CourseScheduleSerializer:          课程安排 CRUD
- StatusTransitionRequestSerializer: 状态切换请求
- ClassStatusRuleSerializer:         可用转换规则
"""

from rest_framework import serializers
from .enums import ClassStatus
from .models import TrainingClass, CourseSchedule, ClassStatusTransition, Position


class PositionSerializer(serializers.ModelSerializer):
    """培训职务精简序列化器（用于班级详情中展示）"""
    post_name = serializers.CharField(source='post.name', read_only=True)

    class Meta:
        model = Position
        fields = ('id', 'name', 'code', 'post_name')


# ===================== 课程安排 =====================


class CourseScheduleSerializer(serializers.ModelSerializer):
    """课程安排序列化器"""
    instructor_name = serializers.CharField(
        source='instructor.username', read_only=True, default=''
    )
    training_class_name = serializers.CharField(
        source='training_class.name', read_only=True, default=''
    )

    class Meta:
        model = CourseSchedule
        fields = (
            'id', 'training_class', 'training_class_name',
            'course_name', 'course_type', 'schedule_date',
            'time_slot', 'location', 'instructor', 'instructor_name',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        """
        检查时段冲突（WBS T-04 验收标准 #1）
        同一班级同一日期同一时段不能重复排课。
        Note: UniqueConstraint 兜底，这里做前端友好提示。
        """
        training_class = attrs.get('training_class')
        schedule_date = attrs.get('schedule_date')
        time_slot = attrs.get('time_slot')

        if training_class and schedule_date and time_slot:
            instance_id = self.instance.id if self.instance else None
            exists = CourseSchedule.objects.filter(
                training_class=training_class,
                schedule_date=schedule_date,
                time_slot=time_slot,
            )
            if instance_id:
                exists = exists.exclude(pk=instance_id)
            if exists.exists():
                raise serializers.ValidationError(
                    f'该时段已有课程安排（{schedule_date} {time_slot}）'
                )
        return attrs


# ===================== 培训班级 =====================


class TrainingClassListSerializer(serializers.ModelSerializer):
    """班级列表（精简字段）"""
    created_by_name = serializers.CharField(
        source='created_by.username', read_only=True, default=''
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    position_name = serializers.CharField(
        source='position.name', read_only=True
    )
    post_name = serializers.CharField(
        source='position.post.name', read_only=True
    )

    class Meta:
        model = TrainingClass
        fields = (
            'id', 'name',
            'position', 'position_name', 'post_name',
            'status', 'status_display',
            'expected_start_date', 'actual_start_date',
            'created_by_name', 'created_at',
        )


class TrainingClassDetailSerializer(serializers.ModelSerializer):
    """班级详情（含课程安排 + position 信息）"""
    created_by_name = serializers.CharField(
        source='created_by.username', read_only=True, default=''
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    position = PositionSerializer(read_only=True)
    course_schedules = CourseScheduleSerializer(
        many=True, read_only=True, source='course_schedules.all'
    )

    class Meta:
        model = TrainingClass
        fields = (
            'id', 'name',
            'position', 'status', 'status_display',
            'expected_start_date', 'actual_start_date',
            'created_by', 'created_by_name',
            'course_schedules',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'status', 'actual_start_date', 'created_at', 'updated_at')


class TrainingClassCreateSerializer(serializers.ModelSerializer):
    """创建班级（status 自动设为 DRAFT，无需传入）"""

    class Meta:
        model = TrainingClass
        fields = (
            'id', 'name', 'position', 'expected_start_date',
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['status'] = ClassStatus.DRAFT
        return super().create(validated_data)


class TrainingClassUpdateSerializer(serializers.ModelSerializer):
    """更新班级（不可修改 status — 通过 status 端点切换）"""

    class Meta:
        model = TrainingClass
        fields = (
            'name', 'position', 'expected_start_date',
        )


# ===================== 状态切换 =====================


class StatusTransitionRequestSerializer(serializers.Serializer):
    """状态切换请求"""
    to_status = serializers.ChoiceField(choices=ClassStatus.choices)
    remark = serializers.CharField(required=False, allow_blank=True, default='')


class ClassStatusRuleSerializer(serializers.Serializer):
    """状态转换规则（用于返回可用转换列表）"""
    to_status = serializers.CharField()
    to_status_display = serializers.CharField()
    precondition = serializers.CharField()
    is_reversible = serializers.BooleanField()