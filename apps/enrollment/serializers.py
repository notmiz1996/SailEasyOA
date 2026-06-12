# apps/enrollment/serializers.py

"""
学员报名序列化器

- EnrollmentListSerializer:       报名列表（含学员信息）
- CreateEnrollmentSerializer:     单条代录（自动查找/创建 Person）
- ImportResultSerializer:         批量导入结果响应
"""

from rest_framework import serializers
from .models import Enrollment, ImportErrorLog


class EnrollmentListSerializer(serializers.ModelSerializer):
    """报名列表（含学员基本信息）"""
    person_name = serializers.CharField(source='person.name', read_only=True)
    person_id_card = serializers.CharField(source='person.id_card', read_only=True)
    person_phone = serializers.CharField(source='person.phone', read_only=True, default='')
    person_gender = serializers.CharField(source='person.gender', read_only=True, default='')
    status_display = serializers.CharField(
        source='get_enrollment_status_display', read_only=True,
    )

    class Meta:
        model = Enrollment
        fields = (
            'id', 'person', 'person_name', 'person_id_card',
            'person_phone', 'person_gender',
            'enrollment_status', 'status_display',
            'enrolled_at', 'checked_in_at',
        )


class CreateEnrollmentSerializer(serializers.Serializer):
    """
    单条代录序列化器

    根据身份证号自动查找或创建 Person 档案，然后创建 Enrollment。
    同一班级同一身份证号重复报名返回 E-ENR-01。
    """
    name = serializers.CharField(max_length=100, label='姓名')
    id_card = serializers.CharField(max_length=18, label='身份证号')
    phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default='',
        label='手机号',
    )
    gender = serializers.ChoiceField(
        choices=[('M', '男'), ('F', '女')], required=False, allow_blank=True, default='',
        label='性别',
    )
    address_detail = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default='',
        label='详细地址',
    )
    emergency_contact = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default='',
        label='紧急联系人',
    )
    emergency_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default='',
        label='紧急联系人电话',
    )

    def validate_id_card(self, value):
        """身份证号基本格式校验（15位或18位）"""
        value = value.strip()
        if len(value) not in (15, 18):
            raise serializers.ValidationError('身份证号必须为15位或18位')
        if len(value) == 18 and value[-1].upper() not in 'X' and not value[-1].isdigit():
            raise serializers.ValidationError('18位身份证号最后一位必须是数字或X')
        if not value[:-1].isdigit() if len(value) == 18 else not value.isdigit():
            raise serializers.ValidationError('身份证号包含非法字符')
        return value

    def validate(self, attrs):
        """检查同一班级是否已存在该身份证号的报名记录"""
        from django.shortcuts import get_object_or_404
        from apps.persons.models import Person
        from apps.training.models import TrainingClass

        id_card = attrs.get('id_card', '')
        training_class = self.context.get('training_class')

        if id_card and training_class:
            person = Person.objects.filter(id_card=id_card).first()
            if person:
                if Enrollment.objects.filter(
                    person=person,
                    training_class=training_class,
                ).exists():
                    raise serializers.ValidationError('该学员已在本班级报名')
        return attrs

    def create(self, validated_data):
        """查找或创建 Person，然后创建 Enrollment"""
        from apps.persons.models import Person

        training_class = self.context['training_class']
        id_card = validated_data.pop('id_card')

        person, created = Person.objects.get_or_create(
            id_card=id_card,
            defaults={
                'name': validated_data.get('name', ''),
                'phone': validated_data.get('phone', ''),
                'gender': validated_data.get('gender', ''),
                'address_detail': validated_data.get('address_detail', ''),
                'emergency_contact': validated_data.get('emergency_contact', ''),
                'emergency_phone': validated_data.get('emergency_phone', ''),
            },
        )

        if not created and not person.name and validated_data.get('name'):
            person.name = validated_data['name']
            person.save(update_fields=['name'])

        enrollment = Enrollment.objects.create(
            person=person,
            training_class=training_class,
        )
        return enrollment


class ImportResultSerializer(serializers.Serializer):
    """批量导入结果响应"""
    task_id = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)