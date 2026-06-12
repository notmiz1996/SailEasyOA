# apps/training/models.py

"""
培训班级核心模型（技术方案书 v1.7）

包含六张表：
1. Post                   — 培训岗位（驾驶岗位/轮机岗位/航线延申/合格证培训/非统考）
2. Position               — 培训职务（一类船长/二类驾驶员等，多对一→Post）
3. TrainingClass          — 培训班级（9态状态机，position FK→Position）
4. CourseSchedule         — 课程安排（半天粒度）
5. ClassStatusTransition  — 班级状态变更日志（审计）
6. ClassStatusRule        — 状态转换规则配置（可配置化）

### 状态机概览（9态）
DRAFT → ENROLLING → ROSTER_GENERATED → SUBMITTED → PENDING_APPROVAL
                                                              ↓
                                                        APPROVED → IN_PROGRESS → FINISHED → ARCHIVED

约束：
- APPROVED / IN_PROGRESS / ARCHIVED 禁止逆向转换
- 所有状态变更统一经过 ClassStatusService.transition()
- 禁止在 View/Serializer 中直接修改 status 字段
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator
from .enums import ClassStatus


# ===================== 岗位 & 职务 =====================


class Post(models.Model):
    """
    培训岗位（基础数据）

    5个岗位：驾驶岗位、轮机岗位、航线延申、合格证培训、非统考
    通过 seed_posts 命令初始化（幂等）。
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID',
    )
    name = models.CharField(
        max_length=50, verbose_name='岗位名称',
        help_text='如：驾驶岗位、轮机岗位',
    )
    code = models.CharField(
        max_length=20, unique=True, verbose_name='岗位编码',
        help_text='如：DRIVING、ENGINE',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'posts'
        verbose_name = '培训岗位'
        verbose_name_plural = '培训岗位'
        ordering = ['code']

    def __str__(self):
        return self.name


class Position(models.Model):
    """
    培训职务（基础数据，多对一→Post）

    18个职务，如：一类船长、二类驾驶员、基本安全培训。
    Position → Post 多对一映射通过 POSITION_MAPPING 常量定义。
    通过 seed_posts 命令初始化（幂等）。
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID',
    )
    name = models.CharField(
        max_length=50, verbose_name='职务名称',
        help_text='如：一类船长、二类驾驶员',
    )
    code = models.CharField(
        max_length=20, unique=True, verbose_name='职务编码',
        help_text='如：CAPTAIN_1、DRIVER_2',
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, verbose_name='所属岗位',
        related_name='positions',
        help_text='多对一：多个职务属于同一岗位',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'positions'
        verbose_name = '培训职务'
        verbose_name_plural = '培训职务'
        ordering = ['post__code', 'code']

    def __str__(self):
        return f'{self.name}（{self.post.name}）'


# ===================== 培训班级 =====================


class TrainingClass(models.Model):
    """
    培训班级（9态状态机）

    状态转换统一经过 ClassStatusService.transition()，禁止直接修改 status。
    培训类型通过 position FK → Position 间接关联 Post（岗位），不再使用硬编码枚举。
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID',
    )
    name = models.CharField(
        max_length=200, unique=True, verbose_name='班级名称',
        help_text='例如：2026年第一期驾驶一类培训班',
    )
    position = models.ForeignKey(
        Position, on_delete=models.PROTECT, verbose_name='培训职务',
        related_name='training_classes',
        help_text='引用 Position 表，如一类船长、二类驾驶员',
    )
    status = models.CharField(
        max_length=30, choices=ClassStatus.choices,
        default=ClassStatus.DRAFT, verbose_name='班级状态', db_index=True,
    )
    expected_start_date = models.DateField(
        verbose_name='预计开班日期',
        help_text='创建班级时填写的计划开班日',
    )
    actual_start_date = models.DateField(
        null=True, blank=True, verbose_name='实际开班日期',
        help_text='状态切换至 IN_PROGRESS 时自动填充',
    )
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='创建人',
        related_name='created_classes',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'training_classes'
        verbose_name = '培训班级'
        verbose_name_plural = '培训班级'
        ordering = ['-created_at']
        indexes = [
            # 列表页按状态+日期筛选
            models.Index(fields=['status', 'expected_start_date'], name='idx_class_status_date'),
        ]

    def __str__(self):
        return f'{self.name}（{self.get_status_display()}）'


# ===================== 课程安排 =====================


class CourseSchedule(models.Model):
    """
    课程安排（半天粒度）

    一对一堂课：一个班级在某个日期的上午/下午上什么课。
    一个班级可以有多条课程安排，构成完整的课程表。

    UNIQUE(training_class, schedule_date, time_slot)
    — 同一班级同一日期同一时段只能安排一门课
    """

    class CourseType(models.TextChoices):
        THEORY = 'theory', '理论课'
        PRACTICAL = 'practical', '实操课'

    class TimeSlot(models.TextChoices):
        MORNING = 'morning', '上午'
        AFTERNOON = 'afternoon', '下午'

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID',
    )
    training_class = models.ForeignKey(
        TrainingClass, on_delete=models.CASCADE,
        verbose_name='所属班级', related_name='course_schedules',
    )
    course_name = models.CharField(
        max_length=200, verbose_name='课程名称',
        help_text='如：船舶操纵、航海英语',
    )
    course_type = models.CharField(
        max_length=20, choices=CourseType.choices, verbose_name='课程类型',
    )
    schedule_date = models.DateField(verbose_name='上课日期')
    time_slot = models.CharField(
        max_length=20, choices=TimeSlot.choices, verbose_name='时段',
    )
    location = models.CharField(
        max_length=200, blank=True, verbose_name='上课地点',
    )
    instructor = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='授课教师',
        related_name='teaching_schedules',
    )

    class Meta:
        db_table = 'course_schedules'
        verbose_name = '课程安排'
        verbose_name_plural = '课程安排'
        ordering = ['schedule_date', 'time_slot']
        constraints = [
            # 同一班级同一天同一时段不能安排两门课（WBS T-04 验收标准#1）
            models.UniqueConstraint(
                fields=['training_class', 'schedule_date', 'time_slot'],
                name='uq_class_date_slot',
            ),
        ]

    def __str__(self):
        return f'{self.training_class.name} - {self.schedule_date} {self.get_time_slot_display()} {self.course_name}'


# ===================== 状态机相关 =====================


class ClassStatusTransition(models.Model):
    """
    班级状态变更日志（审计表）

    每次状态变更都记录一条，包含：操作人、操作时间、状态变更详情。
    与 status 变更在同一个事务中写入（通过 ClassStatusService.transition() 保证）。
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID',
    )
    training_class = models.ForeignKey(
        TrainingClass, on_delete=models.CASCADE,
        verbose_name='所属班级', related_name='status_transitions',
    )
    from_status = models.CharField(max_length=30, verbose_name='原状态')
    to_status = models.CharField(max_length=30, verbose_name='目标状态')
    operator = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='操作人',
    )
    operated_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')
    remark = models.TextField(
        blank=True, verbose_name='备注',
        help_text='如：逆向转换的原因说明',
    )

    class Meta:
        db_table = 'class_status_transitions'
        verbose_name = '状态变更日志'
        verbose_name_plural = '状态变更日志'
        ordering = ['-operated_at']

    def __str__(self):
        return f'{self.training_class.name}: {self.from_status} → {self.to_status}'


class ClassStatusRule(models.Model):
    """
    班级状态转换规则配置表（可配置化）

    用于驱动状态机校验：
    - 当前状态 → 目标状态 是否允许
    - 谁（allowed_role）可以触发
    - 有什么前置条件（precondition）

    种子数据通过 seed_class_rules 命令加载（13 条规则）。
    如需新增/修改规则，数据变更即可，无需改代码。
    """

    class AllowedRole(models.TextChoices):
        ADMIN = 'ADMIN', '教学管理员'
        TEACHER = 'TEACHER', '教学人员'
        PRINCIPAL = 'PRINCIPAL', '校长'
        SYSTEM = 'SYSTEM', '系统自动'

    class Precondition(models.TextChoices):
        NONE = 'NONE', '无前置条件'
        MIN_ENROLLMENT_1 = 'MIN_ENROLLMENT_1', '至少1名已报名学员'
        LOG_SUBMIT_TIME = 'LOG_SUBMIT_TIME', '必须记录递交时间'
        STATS_COMPLETED = 'STATS_COMPLETED', '必须完成出勤统计'
        ALL_COURSES_DONE = 'ALL_COURSES_DONE', '所有课程已结束'

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID',
    )
    from_status = models.CharField(max_length=30, verbose_name='源状态')
    to_status = models.CharField(max_length=30, verbose_name='目标状态')
    allowed_role = models.CharField(
        max_length=20, choices=AllowedRole.choices, verbose_name='允许触发的角色',
    )
    precondition = models.CharField(
        max_length=30, choices=Precondition.choices,
        default=Precondition.NONE, verbose_name='前置条件',
        help_text='枚举常量，通过 match 分支在 Service 层求值',
    )
    is_reversible = models.BooleanField(
        default=False, verbose_name='允许逆向',
        help_text='True=允许从 to_status 回到 from_status',
    )
    remark = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'class_status_rules'
        verbose_name = '状态转换规则'
        verbose_name_plural = '状态转换规则'
        ordering = ['from_status', 'to_status']
        constraints = [
            models.UniqueConstraint(
                fields=['from_status', 'to_status'],
                name='uq_transition_rule',
            ),
        ]

    def __str__(self):
        return f'{self.from_status} → {self.to_status}（{self.allowed_role}）'