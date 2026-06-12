# apps/enrollment/models.py

"""
学员报名模型

包含两张表：
1. Enrollment       — 学员-班级报名关联（一人可参训多个班级）
2. ImportErrorLog   — 批量导入错误日志

### Enrollment 状态机
ENROLLED（已报名） → CHECKED_IN（已报到） → WITHDRAWN（已退学）

约束：
- UNIQUE(person, training_class)：同一人同一班级只能有一条报名记录
- enrollment_status 独立于班级状态，报到后不因班级状态回退而回退
"""

import uuid
from django.db import models


class Enrollment(models.Model):
    """
    学员-班级报名关联

    挂在 Enrollment 上的业务：考勤（AttendanceRecord）、请假（LeaveRequest）
    Person 可参加多个班级，每次报名为独立 Enrollment 记录。
    """

    class EnrollmentStatus(models.TextChoices):
        """学员报名状态"""
        ENROLLED = 'ENROLLED', '已报名'
        CHECKED_IN = 'CHECKED_IN', '已报到'
        WITHDRAWN = 'WITHDRAWN', '已退学'

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID',
    )
    person = models.ForeignKey(
        'persons.Person', on_delete=models.CASCADE,
        verbose_name='学员档案', related_name='enrollments',
    )
    training_class = models.ForeignKey(
        'training.TrainingClass', on_delete=models.CASCADE,
        verbose_name='所属班级', related_name='enrollments',
    )
    enrollment_status = models.CharField(
        max_length=20, choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED, verbose_name='报名状态',
    )
    enrolled_at = models.DateTimeField(
        auto_now_add=True, verbose_name='报名时间',
    )
    checked_in_at = models.DateTimeField(
        null=True, blank=True, verbose_name='报到时间',
        help_text='报到确认时自动填充',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'enrollments'
        verbose_name = '学员报名'
        verbose_name_plural = '学员报名'
        ordering = ['-enrolled_at']
        constraints = [
            # 同一人同一班级只能有一条报名记录（WBS T-05 验收标准 #1）
            models.UniqueConstraint(
                fields=['person', 'training_class'],
                name='uq_person_class',
            ),
        ]

    def __str__(self):
        return f'{self.person.name} → {self.training_class.name}（{self.get_enrollment_status_display()}）'


class ImportErrorLog(models.Model):
    """
    批量导入错误日志

    记录导入过程中每一行的错误详情，用于前端展示导入报告。
    逐行独立事务，失败行不影响成功行。
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID',
    )
    task_id = models.CharField(
        max_length=255, db_index=True, verbose_name='任务ID',
        help_text='Django-Q 任务 ID',
    )
    row_num = models.IntegerField(verbose_name='行号', help_text='Excel 中的行号（从2开始，第1行为表头）')
    error_type = models.CharField(
        max_length=50, verbose_name='错误类型',
        help_text='如：ID_CARD_FORMAT / DUPLICATE / PERSON_CREATE_FAIL',
    )
    error_message = models.TextField(verbose_name='错误消息')
    raw_data = models.JSONField(
        default=dict, verbose_name='原始数据',
        help_text='该行的原始 Excel 数据（JSON）',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'import_error_logs'
        verbose_name = '导入错误日志'
        verbose_name_plural = '导入错误日志'
        ordering = ['task_id', 'row_num']

    def __str__(self):
        return f'Task {self.task_id} Row {self.row_num}: {self.error_type}'