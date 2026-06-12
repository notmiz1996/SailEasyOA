# utils/id_card.py

"""
身份证号校验工具
支持 15 位（旧版）和 18 位（新版）身份证号
"""

import re


def validate_id_card(id_card: str) -> bool:
    """
    校验身份证号格式
    15 位：纯数字
    18 位：前 17 位数字 + 最后一位数字或 X
    """
    if not id_card:
        return False

    # 15 位
    if len(id_card) == 15:
        return bool(re.match(r'^\d{15}$', id_card))

    # 18 位
    if len(id_card) == 18:
        return bool(re.match(r'^\d{17}[\dXx]$', id_card))

    return False


def extract_birth_date(id_card: str) -> str | None:
    """
    从身份证号提取出生日期
    返回格式：YYYY-MM-DD，提取失败返回 None
    15 位：第 7-12 位（YYMMDD），补 19 前缀
    18 位：第 7-14 位（YYYYMMDD）
    """
    if not validate_id_card(id_card):
        return None

    if len(id_card) == 15:
        # 15 位：YYMMDD → 19YYMMDD
        return f"19{id_card[6:12]}"
    else:
        # 18 位：YYYYMMDD
        return id_card[6:14]


def extract_gender(id_card: str) -> str | None:
    """
    从身份证号提取性别
    15 位：第 15 位，奇数=男，偶数=女
    18 位：第 17 位，奇数=男，偶数=女
    """
    if not validate_id_card(id_card):
        return None

    digit = int(id_card[14] if len(id_card) == 15 else id_card[16])
    return '男' if digit % 2 == 1 else '女'