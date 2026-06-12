# utils/region.py

"""
行政区划工具
从 regions.json 加载省市区数据，支持三级联动查询
"""

import json
from pathlib import Path


class RegionService:
    """行政区划服务"""

    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = str(Path(__file__).parent.parent / 'data' / 'regions.json')
        self.data_path = data_path
        self._provinces: list = []
        self._cities: dict = {}
        self._districts: dict = {}

    def load(self):
        """加载行政区划数据"""
        with open(self.data_path, 'r', encoding='utf-8') as f:
            regions = json.load(f)

        for province in regions:
            self._provinces.append({
                'id': province['id'],
                'name': province['name'],
                'code': province.get('code', ''),
            })
            self._cities[province['id']] = []
            for city in province.get('children', []):
                self._cities[province['id']].append({
                    'id': city['id'],
                    'name': city['name'],
                    'code': city.get('code', ''),
                })
                self._districts[city['id']] = []
                for district in city.get('children', []):
                    self._districts[city['id']].append({
                        'id': district['id'],
                        'name': district['name'],
                        'code': district.get('code', ''),
                    })

    def get_provinces(self) -> list[dict]:
        """获取所有省份"""
        if not self._provinces:
            self.load()
        return self._provinces

    def get_cities(self, province_id: int) -> list[dict]:
        """获取指定省份的城市"""
        if not self._cities:
            self.load()
        return self._cities.get(province_id, [])

    def get_districts(self, city_id: int) -> list[dict]:
        """获取指定城市的区县"""
        if not self._districts:
            self.load()
        return self._districts.get(city_id, [])