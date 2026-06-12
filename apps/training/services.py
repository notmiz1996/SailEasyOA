# apps/training/services.py

"""
班级状态机服务（核心业务逻辑）

### 设计原则
1. 状态转换统一经过 ClassStatusService.transition()，禁止跨层直接修改 status
2. 使用 transaction.atomic() 保证状态变更与日志记录原子写入
3. 使用 select_for_update() 行级锁防止并发操作
4. 前置条件通过枚举 + match 分支求值，不解析字符串表达式

### 使用方法
    service = ClassStatusService()
    service.transition(
        class_id=class_id,
        target_status='APPROVED',
        operator=request.user,
        remark='审批通过',
    )
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from loguru import logger

from .enums import ClassStatus
from .models import TrainingClass, ClassStatusRule, ClassStatusTransition


class ClassStatusService:
    """
    班级状态机服务

    提供 transition() 方法处理所有状态变更，包含：
    - 规则校验（from → to 是否允许）
    - 角色校验（operator 是否有权限）
    - 前置条件校验（依赖 match 分支）
    - 行级锁并发控制
    - 审计日志记录
    """

    @transaction.atomic
    def transition(
        self,
        class_id: str,
        target_status: str,
        operator,
        remark: str = '',
    ) -> dict:
        """
        执行班级状态转换

        :param class_id:      班级 UUID
        :param target_status: 目标状态（字符串，如 'APPROVED'）
        :param operator:      操作人（User 实例）
        :param remark:        备注（如逆向转换的原因说明）
        :returns: {
            'class_id': ...,
            'from_status': 'DRAFT',
            'to_status': 'APPROVED',
            'to_status_display': '已审批',
            'available_transitions': [...],
        }
        :raises: ValidationError（规则不满足时抛出）
        """
        # ---- 1. 行级锁获取班级记录 ----
        training_class = TrainingClass.objects.select_for_update().get(pk=class_id)
        from_status = training_class.status

        # ---- 2. 检查幂等（已是目标状态则直接返回成功）----
        if from_status == target_status:
            return self._build_response(training_class, operator)

        # ---- 3. 校验规则是否存在 ----
        try:
            rule = ClassStatusRule.objects.get(
                from_status=from_status,
                to_status=target_status,
            )
        except ClassStatusRule.DoesNotExist:
            available = list(
                ClassStatusRule.objects
                .filter(from_status=from_status)
                .values_list('to_status', flat=True)
            )
            raise ValidationError(
                f'不允许从 [{training_class.get_status_display()}] '
                f'切换到 [{dict(ClassStatus.choices).get(target_status, target_status)}]。'
                f'允许的目标状态：{available}'
            )

        # ---- 4. 校验操作人角色 ----
        if rule.allowed_role == 'SYSTEM':
            pass
        elif not operator or operator.role != rule.allowed_role:
            raise ValidationError(
                f'操作人角色 [{operator.role if operator else "NONE"}] 无权执行此转换。'
                f'需要角色：{rule.allowed_role}'
            )

        # ---- 5. 执行前置条件校验 ----
        self._check_precondition(rule.precondition, training_class)

        # ---- 6. 执行状态变更 ----
        training_class.status = target_status

        if target_status == ClassStatus.IN_PROGRESS:
            training_class.actual_start_date = timezone.now().date()

        training_class.save(update_fields=['status', 'actual_start_date', 'updated_at'])

        # ---- 7. 记录审计日志 ----
        ClassStatusTransition.objects.create(
            training_class=training_class,
            from_status=from_status,
            to_status=target_status,
            operator=operator,
            remark=remark,
        )

        # ---- 8. 业务日志 ----
        op_name = operator.username if operator else 'SYSTEM'
        logger.info(
            f'{op_name} 将班级 [{training_class.name}] 从 '
            f'[{from_status}] 切换到 [{target_status}]'
        )

        return self._build_response(training_class, operator)

    def _check_precondition(self, precondition: str, training_class: TrainingClass):
        """
        前置条件校验
        使用 match 分支求值，新增前置条件时增加枚举值 + 对应分支即可。
        """
        from apps.enrollment.models import Enrollment

        match precondition:
            case 'NONE':
                pass
            case 'MIN_ENROLLMENT_1':
                count = Enrollment.objects.filter(
                    training_class=training_class,
                    enrollment_status='ENROLLED',
                ).count()
                if count < 1:
                    raise ValidationError('班级内至少需要 1 名已报名学员才能生成名册')
            case 'LOG_SUBMIT_TIME':
                pass
            case 'STATS_COMPLETED':
                pass
            case 'ALL_COURSES_DONE':
                from .models import CourseSchedule
                total = CourseSchedule.objects.filter(training_class=training_class).count()
                if total == 0:
                    raise ValidationError('班级没有课程安排，无法结业')
            case _:
                logger.warning(f'未知前置条件：{precondition}，已跳过校验')

    def get_available_transitions(self, training_class: TrainingClass) -> list[dict]:
        """获取班级当前状态允许的所有目标状态"""
        rules = ClassStatusRule.objects.filter(
            from_status=training_class.status,
        )
        return [
            {
                'to_status': rule.to_status,
                'to_status_display': dict(ClassStatus.choices).get(rule.to_status, rule.to_status),
                'precondition': rule.precondition,
                'is_reversible': rule.is_reversible,
            }
            for rule in rules
        ]

    @staticmethod
    def _build_response(training_class: TrainingClass, operator) -> dict:
        """构建标准响应"""
        from .serializers import ClassStatusRuleSerializer

        service = ClassStatusService()
        available = service.get_available_transitions(training_class)

        return {
            'class_id': str(training_class.id),
            'from_status': training_class.status,
            'to_status': training_class.status,
            'to_status_display': training_class.get_status_display(),
            'available_transitions': ClassStatusRuleSerializer(available, many=True).data,
        }