# apps/training/enums.py

"""
班级状态枚举（提取为独立文件，参考技术方案书 v1.7 3.1 节修订）

9态状态机：
DRAFT → ENROLLING → ROSTER_GENERATED → SUBMITTED → PENDING_APPROVAL
                                                              ↓
                                                        APPROVED → IN_PROGRESS → FINISHED → ARCHIVED

约束：
- APPROVED / IN_PROGRESS / ARCHIVED 禁止逆向转换
- 所有状态变更统一经过 ClassStatusService.transition()
"""

from django.db import models


class ClassStatus(models.TextChoices):
    """班级状态枚举（9态，按流转顺序排列）"""
    DRAFT = 'DRAFT', '草稿'
    ENROLLING = 'ENROLLING', '报名中'
    ROSTER_GENERATED = 'ROSTER_GENERATED', '名册已生成'
    SUBMITTED = 'SUBMITTED', '已递交'
    PENDING_APPROVAL = 'PENDING_APPROVAL', '待审批'
    APPROVED = 'APPROVED', '已审批'
    IN_PROGRESS = 'IN_PROGRESS', '进行中'
    FINISHED = 'FINISHED', '已结束'
    ARCHIVED = 'ARCHIVED', '已归档'

# 禁止逆向的状态集合（不可回退）
IRREVERSIBLE_STATUSES = {
    ClassStatus.APPROVED,
    ClassStatus.IN_PROGRESS,
    ClassStatus.ARCHIVED,
}

# 允许报到的班级状态集合
# 学员报到仅允许在开班前，但不能在草稿、已结束和已归档状态中进行报到操作
CHECKIN_ALLOWED_STATUSES = {
    ClassStatus.ENROLLING,
    ClassStatus.ROSTER_GENERATED,
    ClassStatus.SUBMITTED,
    ClassStatus.PENDING_APPROVAL,
    ClassStatus.APPROVED,
}