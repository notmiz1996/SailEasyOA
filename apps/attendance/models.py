# apps/attendance/models.py

"""
考勤记录模型

考勤以半天为粒度，每名学员每天最多两条记录（morning / afternoon）。
请假批准的时段状态自动变为 leave（由 T-10 通知模块联动）。
"""

import uuid
from django.db import models


class TimeSlot(models.TextChoices):
    """时段枚举"""
    MORNING = 'morning', '上午'
    AFTERNOON = 'afternoon', '下午'


class AttendanceStatus(models.TextChoices):
    """考勤状态枚举"""
    PRESENT = 'present', '出勤'
    ABSENT = 'absent', '缺勤'
    LEAVE = 'leave', '请假'


class AttendanceRecord(models.Model):
    """考勤记录"""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID',
    )
    enrollment = models.ForeignKey(
        'enrollment.Enrollment',
        on_delete=models.CASCADE,
        verbose_name='报名记录',
        help_text='关联报名记录（而非 Person），一人多班级时考勤独立',
    )
    training_class = models.ForeignKey(
        'training.TrainingClass',
        on_delete=models.CASCADE,
        verbose_name='培训班级',
    )
    record_date = models.DateField(verbose_name='考勤日期')
    time_slot = models.CharField(
        max_length=10, choices=TimeSlot.choices, verbose_name='时段',
    )
    status = models.CharField(
        max_length=10, choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT, verbose_name='考勤状态',
    )
    created_by = models.ForeignKey(
        'accounts.User',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name='录入人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'attendance_records'
        verbose_name = '考勤记录'
        verbose_name_plural = '考勤记录'
        # UNIQUE 约束：同一报名记录、同一班级、同一日期、同一时段只能有一条考勤
        constraints = [
            models.UniqueConstraint(
                fields=['enrollment', 'training_class', 'record_date', 'time_slot'],
                name='uq_attendance_enrollment_date_slot',
            ),
        ]
        indexes = [
            models.Index(
                fields=['training_class', 'record_date'],
                name='idx_attendance_class_date',
            ),
        ]

    def __str__(self):
        return f'{self.enrollment} | {self.record_date} {self.get_time_slot_display()}'