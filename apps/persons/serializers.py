# apps/persons/serializers.py

"""
Person 序列化器
- PersonSerializer：基础 CRUD，身份证号自动提取性别和出生日期
- PersonCreateSerializer：创建时支持省市区 ID 写入
- PersonLookupSerializer：按身份证号/手机号快速查找（用于报名时关联已有档案）
- RegionSerializer：省市区级联查询
"""

from rest_framework import serializers
from .models import Person, Region
from utils.id_card import validate_id_card


class RegionSerializer(serializers.ModelSerializer):
    """行政区划序列化器"""

    children = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Region
        fields = ('id', 'name', 'level', 'code', 'parent_id', 'children')

    def get_children(self, obj):
        """递归返回下级列表（仅当明确请求 children 时）"""
        # 默认不展开 children，避免返回数据量过大
        return None


class RegionListSerializer(serializers.ModelSerializer):
    """省市区下拉列表用（扁平结构，按 level + parent_id 查询）"""

    class Meta:
        model = Region
        fields = ('id', 'name', 'level', 'code', 'parent_id')


class PersonReadSerializer(serializers.ModelSerializer):
    """人员档案读取（省市区显示名称而非 ID）"""

    province_name = serializers.CharField(source='province.name', read_only=True, default='')
    city_name = serializers.CharField(source='city.name', read_only=True, default='')
    district_name = serializers.CharField(source='district.name', read_only=True, default='')

    class Meta:
        model = Person
        fields = (
            'id', 'name', 'id_card', 'gender', 'birth_date',
            'phone', 'email',
            'province', 'province_name',
            'city', 'city_name',
            'district', 'district_name',
            'address_detail',
            'emergency_contact', 'emergency_phone',
            'openid',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class PersonWriteSerializer(serializers.ModelSerializer):
    """
    人员档案写入（创建/更新）
    省市区传入 ID，允许手动修正性别和出生日期
    """

    class Meta:
        model = Person
        fields = (
            'id', 'name', 'id_card', 'gender', 'birth_date',
            'phone', 'email',
            'province', 'city', 'district',
            'address_detail',
            'emergency_contact', 'emergency_phone',
            'openid',
        )

    def validate_id_card(self, value):
        """校验身份证号格式"""
        if not validate_id_card(value):
            raise serializers.ValidationError('身份证号格式错误（应为15位或18位）')
        return value

    def validate_phone(self, value):
        """手机号非空时校验格式"""
        if value and not value.isdigit():
            raise serializers.ValidationError('手机号必须为数字')
        return value

    def validate(self, attrs):
        """自动从身份证号提取性别和出生日期（如果未手动指定）"""
        id_card = attrs.get('id_card', '')
        if id_card and validate_id_card(id_card):
            from utils.id_card import extract_gender, extract_birth_date
            # 性别：手动指定优先，未指定则自动提取
            if not attrs.get('gender'):
                attrs['gender'] = extract_gender(id_card) or ''
            # 出生日期：手动指定优先，未指定则自动提取
            if not attrs.get('birth_date'):
                birth_str = extract_birth_date(id_card)
                if birth_str:
                    from datetime import datetime
                    attrs['birth_date'] = datetime.strptime(birth_str, '%Y%m%d').date()
        return attrs


class PersonLookupSerializer(serializers.Serializer):
    """
    按身份证号或手机号快速查找已有档案
    用于报名时判断该学员是否已有 Person 记录

    GET /api/v1/persons/lookup/?id_card=440101199001011234
    或
    GET /api/v1/persons/lookup/?phone=13800138000
    """

    id_card = serializers.CharField(max_length=18, required=False)
    phone = serializers.CharField(max_length=20, required=False)

    def validate(self, attrs):
        if not attrs.get('id_card') and not attrs.get('phone'):
            raise serializers.ValidationError('请提供 id_card 或 phone 其中一个参数')
        return attrs