# -*- coding: utf-8 -*-
from dependencies import QuestDBSession
from typing import List, Any, Dict
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from crud.configCrud import get_storage_config
from sqlalchemy import  text
from utils.query import require_allowed


ALLOWED_TABLE_PREFIXES = {
    "storage_usage",
    "aggregate",
    "volume",
    "qtree",
    "project",
    "group",
}
ALLOWED_INDICATORS = {"used", "used_ratio", "file_used"}


def _normalize_indicator(indicator: str) -> str:
    if indicator == "use_ratio":
        return "used_ratio"
    return require_allowed(indicator, ALLOWED_INDICATORS, "indicator")


def _table_info(table_prefix: str) -> tuple[str, str]:
    table_prefix = require_allowed(table_prefix, ALLOWED_TABLE_PREFIXES, "table_prefix")
    if table_prefix == "storage_usage":
        return "storage_usage", "storage_usages"
    return table_prefix, f"{table_prefix}_storage_usages"

def get_storage_real_time(columns: List[str], table_prefix: str, attribute_id: int, start_time: datetime,
                          end_time: datetime, storage_config: Any):
    attribute, table_name = _table_info(table_prefix)
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)
    if end_time - timedelta(days=30) > start_time:
        sample_by = " SAMPLE BY 1d"
    elif end_time - timedelta(days=7) > start_time:
        sample_by = " SAMPLE BY 1h"
    else:
        sample_by = " SAMPLE BY 1m"
    columns = [_normalize_indicator(column) for column in columns]
    max_columns = [f"max({column})" for column in columns]
    columns_str = ",".join(max_columns)
    select_command = f"""
            SELECT {columns_str}, updated_at
            FROM {table_name}
            WHERE {attribute}_id = :attribute_id
            AND updated_at BETWEEN :start_time AND :end_time
            {sample_by};
            """
    with QuestDBSession(config=storage_config) as conn:
        result = conn.execute(
            text(select_command),
            {"attribute_id": str(attribute_id), "start_time": str(start_time), "end_time": str(end_time)},
        ).fetchall()
    return result


def process_result_data(result: List[Any], columns: List[str]) -> Dict[str, List[List[Any]]]:
    data = {}
    for i, column in enumerate(columns):
        source = []
        for item in result:
            row = [item[-1].strftime("%Y-%m-%d %H:%M:00"), item[i]]
            source.append(row)
        data[column] = source
    return data


def get_real_time_data_by_id(db: Session, attribute_id: int, start_time: datetime | None = None,
                             end_time: datetime | None = None, indicator: str = 'used',
                             table_prefix: str = 'storage_usage'):
    if start_time is None and end_time is None:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
    storage_config = get_storage_config(db=db)
    indicator = _normalize_indicator(indicator)
    columns = [indicator]
    result = get_storage_real_time(columns=columns, attribute_id=attribute_id,
                                   start_time=start_time, end_time=end_time, table_prefix=table_prefix,
                                   storage_config=storage_config)
    data = process_result_data(result, columns)
    return data[indicator]


def get_real_time_data_by_ids(db: Session, attribute_ids: list[int], start_time: datetime | None = None,
                              end_time: datetime | None = None, indicator: str = 'used',
                              table_prefix: str = 'storage_usage'):
    ids_list = []
    if start_time is None and end_time is None:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
    storage_config = get_storage_config(db=db)
    indicator = _normalize_indicator(indicator)
    columns = [indicator]
    for attribute_id in attribute_ids:
        result = get_storage_real_time(columns=columns, attribute_id=attribute_id,
                                       start_time=start_time, end_time=end_time, table_prefix=table_prefix,
                                       storage_config=storage_config)
        data = process_result_data(result, columns)

        ids_list.append(data[indicator])
    return ids_list


def get_high_avg_usage(table_prefix: str, storage_config: Any, end_time: datetime = datetime.now() - timedelta(hours=1),
                       threshold: int = 90):
    attribute, table_name = _table_info(table_prefix)
    select_command = f"""
        SELECT {attribute}_id,avg_use_ratio
        FROM (
            SELECT
                {attribute}_id,
                avg(used_ratio) AS avg_use_ratio
            FROM
                {table_name}
            WHERE
                updated_at > :end_time
            GROUP BY
                {attribute}_id
        )
        WHERE
            avg_use_ratio >= :threshold;
    """
    with QuestDBSession(config=storage_config) as conn:
        result = conn.execute(text(select_command), {"end_time": str(end_time), "threshold": threshold}).fetchall()
    return result


def get_cluster_storage_real_time(start_time: datetime,
                                  end_time: datetime, storage_config: Any, group_by_day: bool = False):
    sample_by = "SAMPLE BY 1d " if group_by_day is True else "SAMPLE BY 1m"
    select_command = f"""
            SELECT
                SUM(max_used) AS total_max_used,
                 updated_at,
            FROM (
                SELECT
                    max(used) as max_used,
                    updated_at as updated_at,
                    aggregate_id,
                FROM
                    aggregate_storage_usages
                WHERE  updated_at BETWEEN :start_time AND :end_time
                {sample_by}
            )
            GROUP BY updated_at
            ORDER BY updated_at;
    """
    with QuestDBSession(config=storage_config) as conn:
        result = conn.execute(text(select_command), {"start_time": str(start_time), "end_time": str(end_time)}).fetchall()
    return result


def get_project_storage_usage(storage_config: Any, start_time: datetime | None = None,
                              end_time: datetime | None = None, project_id: int = None):
    select_command = f"SELECT project_id, avg(use_ratio),max(use_ratio) FROM project_storage_usages"
    query_conditions = []
    params = {}
    if project_id:
        query_conditions.append(f"project_id = :attribute_id")
        params['attribute_id']  = str( project_id)
    if start_time and end_time:
        query_conditions.append('updated_at BETWEEN :start_time AND :end_time')
        params['start_time'] = str(start_time)
        params['end_time'] = str(end_time)
    if query_conditions:
        select_command += " WHERE " + " AND ".join(query_conditions)
    select_command += f" GROUP BY project_id"
    with QuestDBSession(config=storage_config) as conn:
        dbs = conn.execute(text(select_command), params).fetchall()

        result = {}
        for db in dbs:
            project_id_val = db[0]
            # 跳过无效的project_id
            if project_id_val is None:
                continue
            project_id_int = int(project_id_val)
            # 安全处理可能为None的统计值
            avg_ratio = db[1] if db[1] is not None else 0.0
            max_ratio = db[2] if db[2] is not None else 0.0

            # 四舍五入，确保是浮点数
            try:
                avg_rounded = round(float(avg_ratio), 1)
                max_rounded = round(float(max_ratio), 1)
            except (ValueError, TypeError):
                avg_rounded = 0.0
                max_rounded = 0.0

            result[project_id_int] = {
                'avg_suut': avg_rounded,
                'max_suut': max_rounded,
            }
    return result


def get_storage_cluster_real_time(db: Session, storage_cluster_id: int, start_time: datetime | None = None,
                                  end_time: datetime | None = None, indicator: str = 'used'):
    indicator = _normalize_indicator(indicator)
    if start_time is None and end_time is None:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)

    if end_time - timedelta(days=30) > start_time:
        sample_by = " SAMPLE BY 1d"
    elif end_time - timedelta(days=7) > start_time:
        sample_by = " SAMPLE BY 1h"
    else:
        sample_by = " SAMPLE BY 1m"

    storage_config = get_storage_config(db=db)
    select_command = f"""
        SELECT max({indicator}), updated_at
        FROM storage_cluster_storage_usages
        WHERE storage_cluster_id = :storage_cluster_id
        AND updated_at BETWEEN :start_time AND :end_time
        {sample_by};
    """

    with QuestDBSession(config=storage_config) as conn:
        result = conn.execute(
            text(select_command),
            {"storage_cluster_id": str(storage_cluster_id), "start_time": str(start_time), "end_time": str(end_time)},
        ).fetchall()

    return [[item[1].strftime("%Y-%m-%d %H:%M:00"), item[0]] for item in result]
