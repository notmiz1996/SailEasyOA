# apps/training/management/commands/seed_posts.py

"""
初始化培训岗位 & 职务种子数据（5 个岗位 + 18 个职务）

用法：
  python manage.py seed_posts             # 插入所有数据（幂等）
  python manage.py seed_posts --clear     # 清空并重新插入

数据来源：技术方案书 v1.7 2.1 节 POSITION_MAPPING
特点：幂等设计，多次执行不会产生重复数据
"""

from django.core.management.base import BaseCommand
from apps.training.models import Post, Position


# 5 个岗位
POSTS = [
    {'code': 'DRIVING', 'name': '驾驶岗位'},
    {'code': 'ENGINE', 'name': '轮机岗位'},
    {'code': 'ROUTE_EXT', 'name': '航线延申'},
    {'code': 'CERT_TRAIN', 'name': '合格证培训'},
    {'code': 'NON_EXAM', 'name': '非统考'},
]

# 18 个职务（Position → Post 映射）
# 格式：(name, code, post_code)
POSITIONS = [
    # 驾驶岗位
    ('一类船长', 'CAPTAIN_1', 'DRIVING'),
    ('一类大副', 'CHIEF_OFFICER_1', 'DRIVING'),
    ('一类三副', 'THIRD_OFFICER_1', 'DRIVING'),
    ('二类船长', 'CAPTAIN_2', 'DRIVING'),
    ('二类驾驶员', 'DRIVER_2', 'DRIVING'),
    # 轮机岗位
    ('一类轮机长', 'CHIEF_ENGINEER_1', 'ENGINE'),
    ('一类大管轮', 'FIRST_ENGINEER_1', 'ENGINE'),
    ('一类三管轮', 'THIRD_ENGINEER_1', 'ENGINE'),
    ('二类轮机长', 'CHIEF_ENGINEER_2', 'ENGINE'),
    ('二类轮机员', 'ENGINEER_2', 'ENGINE'),
    # 航线延申
    ('西江航线', 'ROUTE_XIJIANG', 'ROUTE_EXT'),
    ('珠江航线', 'ROUTE_ZHUJIANG', 'ROUTE_EXT'),
    ('北江航线', 'ROUTE_BEIJIANG', 'ROUTE_EXT'),
    ('东江航线', 'ROUTE_DONGJIANG', 'ROUTE_EXT'),
    ('口门外航线', 'ROUTE_ESTUARY', 'ROUTE_EXT'),
    # 合格证培训
    ('基本安全培训', 'BASIC_SAFETY', 'CERT_TRAIN'),
    ('客船特殊培训', 'PASSENGER_SPECIAL', 'CERT_TRAIN'),
    # 非统考
    ('未满100总吨内河船舶驾驶员培训', 'INLAND_100T', 'NON_EXAM'),
]


class Command(BaseCommand):
    help = '初始化培训岗位 & 职务种子数据（5 岗位 + 18 职务，幂等）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清空所有岗位/职务后重新插入',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('正在清空岗位/职务数据...'))
            Position.objects.all().delete()
            Post.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('已清空'))

        # ---- 插入岗位 ----
        post_created = 0
        post_skipped = 0
        post_map = {}

        for p in POSTS:
            obj, is_new = Post.objects.get_or_create(
                code=p['code'],
                defaults={'name': p['name']},
            )
            post_map[p['code']] = obj
            if is_new:
                post_created += 1
            else:
                post_skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'岗位初始化完成，共 {Post.objects.count()} 个（新增 {post_created}，跳过 {post_skipped}）'
        ))

        # ---- 插入职务 ----
        pos_created = 0
        pos_skipped = 0

        for name, code, post_code in POSITIONS:
            post = post_map.get(post_code)
            if not post:
                self.stdout.write(self.style.WARNING(f'岗位编码 {post_code} 不存在，跳过职务 {name}'))
                continue

            _, is_new = Position.objects.get_or_create(
                code=code,
                defaults={'name': name, 'post': post},
            )
            if is_new:
                pos_created += 1
            else:
                pos_skipped += 1

        total_pos = Position.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'职务初始化完成，共 {total_pos} 个（新增 {pos_created}，跳过 {pos_skipped}）'
        ))