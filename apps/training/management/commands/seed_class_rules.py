# apps/training/management/commands/seed_class_rules.py

"""
初始化班级状态转换规则种子数据（13 条）

用法：
  python manage.py seed_class_rules          # 插入所有规则（幂等）
  python manage.py seed_class_rules --clear  # 清空并重新插入

规则来源：技术方案书 3.1 节「状态转换约束表」
特点：幂等设计，多次执行不会产生重复数据
"""

from django.core.management.base import BaseCommand
from apps.training.models import ClassStatusRule


# 13 条状态转换规则（与技术方案书 3.1 节完全对齐）
# 格式：(from_status, to_status, allowed_role, precondition, is_reversible, remark)
RULES = [
    ('DRAFT', 'ENROLLING', 'ADMIN', 'NONE', True, '开始招生'),
    ('ENROLLING', 'ROSTER_GENERATED', 'ADMIN', 'MIN_ENROLLMENT_1', True, '生成名册，至少需要1名学员'),
    ('ENROLLING', 'DRAFT', 'ADMIN', 'NONE', True, '退回草稿，已报名学员变为待关联'),
    ('ROSTER_GENERATED', 'SUBMITTED', 'ADMIN', 'LOG_SUBMIT_TIME', False, '递交名册，需记录递交时间'),
    ('ROSTER_GENERATED', 'ENROLLING', 'ADMIN', 'NONE', True, '退回报名中，重新生成名册'),
    ('SUBMITTED', 'PENDING_APPROVAL', 'ADMIN', 'NONE', False, '系统自动推进至待审批'),
    ('PENDING_APPROVAL', 'APPROVED', 'ADMIN', 'NONE', False, '审批通过，需记录审批结果'),
    ('APPROVED', 'IN_PROGRESS', 'ADMIN', 'NONE', False, '开班（禁止逆向）'),
    ('IN_PROGRESS', 'FINISHED', 'ADMIN', 'ALL_COURSES_DONE', False, '结业（禁止逆向）'),
    ('FINISHED', 'ARCHIVED', 'ADMIN', 'STATS_COMPLETED', False, '归档（禁止逆向）'),
    ('FINISHED', 'IN_PROGRESS', 'ADMIN', 'NONE', True, '仅补录考勤时使用，需记录原因'),
    ('DRAFT', 'ARCHIVED', 'ADMIN', 'NONE', False, '直接归档（未开班的班级）'),
    ('ENROLLING', 'ARCHIVED', 'ADMIN', 'NONE', False, '直接归档（招生中的班级）'),
]


class Command(BaseCommand):
    help = '初始化班级状态转换规则（13 条，幂等）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清空所有规则后重新插入',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('正在清空状态转换规则...'))
            ClassStatusRule.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('已清空'))

        created = 0
        skipped = 0

        for from_status, to_status, allowed_role, precondition, is_reversible, remark in RULES:
            _, is_new = ClassStatusRule.objects.get_or_create(
                from_status=from_status,
                to_status=to_status,
                defaults={
                    'allowed_role': allowed_role,
                    'precondition': precondition,
                    'is_reversible': is_reversible,
                    'remark': remark,
                },
            )
            if is_new:
                created += 1
            else:
                skipped += 1

        total = ClassStatusRule.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'状态转换规则初始化完成，共 {total} 条（新增 {created}，跳过 {skipped}）'
        ))