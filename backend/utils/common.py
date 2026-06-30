# -*- coding: utf-8 -*-
from datetime import datetime
import re


def format_to_gb(value):
    """
    Convert memory and storage values in T, G, M to gigabytes (G).

    Args:
    - value (str): The value string to convert, e.g., "638.4G", "1.2T", "500M".

    Returns:
    - float: The value converted to gigabytes.
    """
    if value.endswith('T'):
        return round(float(value[:-1]) * 1024, 2)
    elif value.endswith('G'):
        return round(float(value[:-1]), 2)
    elif value.endswith('M'):
        return round(float(value[:-1]) / 1024, 2)
    elif value.endswith('K'):
        return round(float(value[:-1]) / 1024 / 1024, 2)
    else:
        try:
            return float(value)
        except ValueError:
            return None


def scientific_notation_to_number(s):
    try:
        return int(float(s))
    except ValueError:
        return None


def percent_string_to_float(s):
    try:
        return round(float(s.strip('%')), 2)
    except ValueError:
        return None


def convert_value(value):
    try:
        if value == "-":
            return 0.0
        # 移除G或T单位，并将T转换为对应的G值
        value = re.sub(r'([0-9.]+)[T]', lambda m: str(float(m.group(1)) * 1024), value)
        value = re.sub(r'([0-9.]+)[G]', lambda m: m.group(1), value)
        value = re.sub(r'([0-9.]+)[M]', lambda m: str(float(m.group(1)) / 1024), value)
        # 移除百分号，并将结果除以100
        if value.endswith('%'):
            return float(value.strip('*')[:-1])
        if value.startswith('*'):
            return float(value[1:])
        # 直接转换为浮点数
        return float(value)
    except ValueError:
        return value


def convert_timestamp_to_datetime(end_time_ms: int | str) -> datetime:
    end_time_s = int(end_time_ms) / 1000

    end_time_dt = datetime.fromtimestamp(end_time_s)

    return end_time_dt


def convert_GB_to_TB(value: int | str | float|None) -> float:
    if value is None:
        return 0
    if isinstance(value, str):
        value = int(value)
    return round(value / 1024, 2)
