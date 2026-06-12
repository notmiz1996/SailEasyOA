# apps/persons/models.py

"""
人员档案与行政区划模型

Person（人员基础档案）
  - 身份证号（id_card）为唯一标识，同一人可参加多个班级
  - 手机号（phone）不做唯一约束：允许同一号码被多人使用
  - 地址采用省市区三级外键（Region），支持级联下拉选择

Region（行政区划）
  - 自引用树形结构：省 → 市 → 区
  - GB/T 2260 行政区划代码，用于数据标准化
  - 种子数据通过 seed_regions 管理命令加载
"""

import uuid
from django.db import models
from utils.id_card import validate_id_card, extract_birth_date, extract_gender


class Region(models.Model):
    """
    行政区划（省/市/三级）
    自引用(parent_id)实现省市区树形结构

    数据来源：GB/T 2260 中华人民共和国行政区划代码
    """

    id = models.IntegerField(primary_key=True, verbose_name='编码')
    name = models.CharField(max_length=50, verbose_name='名称')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='上级行政区划',
        related_name='children',
    )
    level = models.IntegerField(
        verbose_name='行政级别',
        help_text='1=省/直辖市/自治区，2=地级市/自治州，3=区/县/县级市',
    )
    code = models.CharField(
        max_length=20,
        verbose_name='行政区划代码',
        help_text='GB/T 2260 六位数字代码',
    )

    class Meta:
        db_table = 'regions'
        verbose_name = '行政区划'
        verbose_name_plural = '行政区划'
        ordering = ['code']
        # 按 parent + level 查询的复合索引（省市区级联查询）
        indexes = [
            models.Index(fields=['parent', 'level'], name='idx_region_parent_level'),
        ]

    def __str__(self):
        prefix = {1: '', 2: '', 3: ''}.get(self.level, '')
        return f'{prefix}{self.name}'


class Person(models.Model):
    """
    人员基础档案（学员和教职员工共用）

    ### 核心设计原则
    1. 身份证号（id_card）是唯一业务标识
    2. 手机号（phone）不做唯一约束——允许父母子女共用
    3. openid 唯一（微信登录），可为空（未绑定微信）
    4. 创建后不可删除（软删除用 is_active），仅允许更新
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID',
    )
    name = models.CharField(
        max_length=100,
        verbose_name='姓名',
    )
    id_card = models.CharField(
        max_length=18,
        unique=True,
        verbose_name='身份证号',
        help_text='15位（旧版）或18位（新版），系统唯一标识',
        db_index=True,  # 频繁按身份证号查询，单列索引
    )
    gender = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='性别',
        help_text='可从身份证号自动提取，也可手动修改',
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='出生日期',
        help_text='可从身份证号自动提取',
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='手机号码',
        help_text='不做唯一约束——允许父母子女共用同一号码',
    )
    email = models.EmailField(
        max_length=100,
        blank=True,
        verbose_name='电子邮箱',
    )

    # --- 地址（省市区三级外键） ---
    province = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='省',
        related_name='persons_province',
    )
    city = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='市',
        related_name='persons_city',
    )
    district = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='区',
        related_name='persons_district',
    )
    address_detail = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='详细地址',
        help_text='门牌号/街道等具体地址',
    )

    # --- 紧急联系人 ---
    emergency_contact = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='紧急联系人',
    )
    emergency_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='紧急联系人电话',
    )

    # --- 微信 ---
    openid = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        verbose_name='微信 OpenID',
        help_text='微信小程序登录标识，为空表示未绑定微信',
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'persons'
        verbose_name = '人员档案'
        verbose_name_plural = '人员档案'
        ordering = ['-created_at']
        # 身份证号已有 unique + db_index；手机号常用查询
        indexes = [
            models.Index(fields=['phone'], name='idx_person_phone'),
        ]

    def __str__(self):
        return f'{self.name} ({self.id_card[-4:]})'

    def save(self, *args, **kwargs):
        """
        保存时自动从身份证号提取性别和出生日期
        （如果对应字段为空）
        """
        if self.id_card and validate_id_card(self.id_card):
            if not self.gender:
                self.gender = extract_gender(self.id_card) or ''
            if not self.birth_date:
                birth_str = extract_birth_date(self.id_card)
                if birth_str:
                    from datetime import datetime
                    self.birth_date = datetime.strptime(birth_str, '%Y%m%d').date()
        super().save(*args, **kwargs)