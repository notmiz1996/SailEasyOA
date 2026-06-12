# apps/persons/management/commands/seed_regions.py

"""
初始化行政区划种子数据（GB/T 2260）

数据来源：ok_data_level3.csv（省市区三级，3639 条）
文件位置：{BASE_DIR}/data/regions/ok_data_level3.csv

用法：
  python manage.py seed_regions                # 插入所有数据（幂等）
  python manage.py seed_regions --clear        # 清空并重新插入
  python manage.py seed_regions --csv-path     # 指定自定义 CSV 路径

### 为什么从 CSV 读取而不是硬编码？
1. 全国省市区 3639 条，硬编码在 py 文件中过于臃肿
2. CSV 独立管理，方便后续数据更新（仅替换 CSV 文件即可）
3. 幂等设计，重复执行不会产生重复数据
"""

import csv
import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.persons.models import Region


class Command(BaseCommand):
    help = '从 ok_data_level3.csv 初始化省市区三级数据（幂等）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清空所有区域数据后重新插入',
        )
        parser.add_argument(
            '--csv-path',
            type=str,
            default='',
            help='指定 ok_data_level3.csv 的路径（默认：<BASE_DIR>/data/regions/ok_data_level3.csv）',
        )

    def handle(self, *args, **options):
        start_time = time.perf_counter()

        # ---------- 确定 CSV 文件路径 ----------
        if options['csv_path']:
            csv_path = options['csv_path']
        else:
            csv_path = os.path.join(settings.BASE_DIR, 'data', 'regions', 'ok_data_level3.csv')

        if not os.path.exists(csv_path):
            raise CommandError(
                f'CSV 文件不存在：{csv_path}\n'
                f'请将 ok_data_level3.csv 复制到项目 data/regions/ 目录下，'
                f'或使用 --csv-path 指定自定义路径。'
            )

        # ---------- 可选：清空 ----------
        if options['clear']:
            self.stdout.write(self.style.WARNING('正在清空行政区划数据...'))
            Region.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('已清空'))
            # 重置数据库序列（SQLite 下无需操作，PostgreSQL 需要 RESTART IDENTITY）

        # ---------- 读取 CSV（按 deep 升序排序，确保父级先存在） ----------
        self.stdout.write(self.style.NOTICE('正在读取 CSV 文件...'))
        rows = self._read_csv(csv_path)
        total = len(rows)

        deep_0 = sum(1 for r in rows if r['deep'] == 0)
        deep_1 = sum(1 for r in rows if r['deep'] == 1)
        deep_2 = sum(1 for r in rows if r['deep'] == 2)

        self.stdout.write(f'读取完成：共 {total} 条记录')
        self.stdout.write(f'  省级（deep=0）：{deep_0} 条')
        self.stdout.write(f'  地市级（deep=1）：{deep_1} 条')
        self.stdout.write(f'  区县级（deep=2）：{deep_2} 条')

        # ---------- 开始导入（带进度显示） ----------
        self.stdout.write(self.style.NOTICE('开始导入数据库...'))
        created = 0
        skipped = 0
        errors = []
        batch_start = time.perf_counter()

        for index, row in enumerate(rows, start=1):
            region_id = int(row['id'])
            parent_id = int(row['pid']) if row['pid'] and int(row['pid']) > 0 else None
            level = int(row['deep']) + 1  # CSV: 0=省 → 模型: 1=省
            code = row.get('ext_id', '').strip()

            try:
                _, is_new = Region.objects.get_or_create(
                    id=region_id,
                    defaults={
                        'name': row['name'],
                        'parent_id': parent_id,
                        'level': level,
                        'code': code,
                    },
                )
                if is_new:
                    created += 1
                else:
                    skipped += 1
            except Exception as e:
                errors.append(f'id={region_id} name={row["name"]}: {e}')

            # ---- 进度显示：每 500 行或最后一行输出一次 ----
            if index % 500 == 0 or index == total:
                elapsed = time.perf_counter() - batch_start
                pct = index / total * 100
                rate = index / elapsed if elapsed > 0 else 0
                self.stdout.write(
                    f'  进度：{index}/{total} ({pct:.1f}%) '
                    f'| 已用 {elapsed:.1f}s '
                    f'| 速度 {rate:.0f} 条/秒'
                )

        # ---------- 输出结果 ----------
        elapsed_total = time.perf_counter() - start_time
        total_in_db = Region.objects.count()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'导入完成！总计 {total_in_db} 条记录（总耗时 {elapsed_total:.2f}s）'
        ))
        self.stdout.write(f'  新增：{created} 条')
        self.stdout.write(f'  已存在跳过：{skipped} 条')

        # 性能摘要
        if total > 0:
            avg_speed = total / elapsed_total
            self.stdout.write(f'  平均速度：{avg_speed:.0f} 条/秒')

        if errors:
            self.stdout.write(self.style.WARNING(f'错误：{len(errors)} 条'))
            for err in errors[:5]:  # 最多显示前 5 条错误
                self.stdout.write(self.style.ERROR(f'  {err}'))

    @staticmethod
    def _read_csv(csv_path: str) -> list[dict]:
        """
        读取 CSV 文件并返回按 deep 排序的行列表

        CSV 列：
          id,pid,deep,name,pinyin_prefix,pinyin,ext_id,ext_name

        处理要点：
          - UTF-8 BOM 以 utf-8-sig 编码打开（头两个字节 \\ufeff 自动剥离）
          - 按 deep 升序排序，保证父级记录先于子级插入
          - 字段值去空白
        """
        with open(csv_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = []
            for line in reader:
                rows.append({
                    'id': line['id'].strip(),
                    'pid': line['pid'].strip(),
                    'deep': int(line['deep']),
                    'name': line['name'].strip(),
                    'pinyin_prefix': line.get('pinyin_prefix', '').strip(),
                    'pinyin': line.get('pinyin', '').strip(),
                    'ext_id': line.get('ext_id', '').strip(),
                    'ext_name': line.get('ext_name', '').strip(),
                })

        # 按 deep 升序排序，保证父级先创建
        rows.sort(key=lambda r: r['deep'])
        return rows