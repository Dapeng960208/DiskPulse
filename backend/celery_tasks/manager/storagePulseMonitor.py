# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from schemas.storageUsageSchema import StorageUsageBase
from schemas.volumeSchema import VolumeBase
from utils.netAppClient import NetAppClient
from utils.isilonClient import IsilonClient
from schemas import aggregateSchema, volumeSchema, qtreeSchema, storageUsageSchema
from models import Aggregate, Volume, Qtree, Group, StorageUsage, User, StorageCluster
from sqlalchemy import func, text, update
from dependencies import QuestDBSession
from typing import List, Dict, Any, Optional


def _bytes_to_gb(value: Any) -> Optional[float]:
    """将字节转换为 GB，保留两位小数。value 为 None 或 -1 时返回 None。"""
    if value is None or value == -1:
        return None
    try:
        return round(float(value) / (1024 ** 3), 2)
    except (TypeError, ValueError):
        return None


def _quota_limit_to_gb(value: Any) -> Optional[float]:
    """Quota limit 为 0、-1 或缺失时视为未设置。"""
    if value in (None, 0, -1):
        return None
    return _bytes_to_gb(value)


def _calculate_use_ratio(used: Optional[float], limit: Optional[float]) -> Optional[float]:
    if used is None or not limit or limit <= 0:
        return None
    return round(used / limit * 100, 2)


class StoragePulseMonitor:
    """
    统一的存储监控类，支持 NetApp ONTAP 和 Isilon OneFS。
    通过 REST API 采集存储数据，并写入 PostgreSQL 和 QuestDB。
    """

    def __init__(self, db, logger, storage_cluster_id: int, snapshot=None):
        """
        初始化存储监控器

        Args:
            db: 数据库会话
            logger: 日志记录器
            storage_cluster_id: StorageCluster 表中的集群 ID
        """
        self.db = db
        self.logger = logger
        self.storage_cluster_id = storage_cluster_id
        self.snapshot = snapshot
        self.group_snapshots = {
            row["group_id"]: row
            for row in (snapshot or {}).get("rows", ())
            if row.get("group_id") is not None
        }
        self.storage_cluster: StorageCluster = db.query(StorageCluster).filter_by(
            id=storage_cluster_id, is_active=True).first()
        if self.storage_cluster is None:
            raise ValueError(f"StorageCluster with id={storage_cluster_id} not found")
        self.storage_type = (
            (snapshot or {}).get("storage_type") or self.storage_cluster.storage_type
        ).lower()
        self.storage_cluster_name = (
            (snapshot or {}).get("storage_cluster_name") or self.storage_cluster.name
        )
        self.client = None

        if self.storage_type not in ('netapp', 'isilon'):
            raise ValueError(f"Unsupported storage type: {self.storage_type}")

    @property
    def _log_prefix(self):
        """日志前缀"""
        type_name = 'NetApp' if self.storage_type == 'netapp' else 'Isilon'
        return f"[StoragePulse|{type_name}|{self.storage_cluster_name}]"

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def start(self):
        """启动监控流程"""
        self.setup()
        self.execute_data_collection()
        self.cleanup()

    def collect_postgres(self):
        """Collect and flush PostgreSQL data inside the caller's transaction."""
        self.setup()
        self.execute_data_collection(include_questdb=False)
        return None

    def write_questdb(self, _metrics=None):
        """Write time-series data after the PostgreSQL transaction committed."""
        self.insert_metrics_to_questdb('storage_usages', self.db.query(StorageUsage).filter(
            StorageUsage.used > 0, StorageUsage.storage_cluster_id == self.storage_cluster_id).all())
        self.insert_metrics_to_questdb('qtree', self.db.query(Qtree).filter(
            Qtree.used >= 0, Qtree.storage_cluster_id == self.storage_cluster_id).all())
        self.insert_metrics_to_questdb('volume', self.db.query(Volume).filter(
            Volume.used >= 0, Volume.storage_cluster_id == self.storage_cluster_id).all())
        group_query = self.db.query(Group).filter(
            Group.enable_monitoring.is_(True),
            Group.storage_cluster_id == self.storage_cluster_id)
        self.insert_metrics_to_questdb('group', group_query.all())
        self.insert_metrics_to_questdb('aggregate', self.db.query(Aggregate).filter(
            Aggregate.used >= 0, Aggregate.storage_cluster_id == self.storage_cluster_id).all())
        self.insert_metrics_to_questdb('storage_cluster', [self.storage_cluster])

    def setup(self):
        """初始化客户端连接"""
        cluster = self.snapshot or {}
        hostname = cluster.get("storage_host", self.storage_cluster.storage_host)
        username = cluster.get("storage_user", self.storage_cluster.storage_user)
        password = cluster.get("storage_password", self.storage_cluster.storage_password)
        configured_port = cluster.get("storage_port", self.storage_cluster.storage_port)
        protocol = cluster.get("protocol", self.storage_cluster.protocol)
        tls_verify = cluster.get("tls_verify", self.storage_cluster.tls_verify)
        if protocol == "http":
            tls_verify = False
            self.logger.warning(f"{self._log_prefix} storage API uses unencrypted HTTP")
        elif not tls_verify:
            self.logger.warning(f"{self._log_prefix} TLS certificate verification is disabled")
            disable_warnings(InsecureRequestWarning)
        if self.storage_type == 'netapp':
            self.client = NetAppClient(
                hostname=hostname,
                username=username,
                password=password,
                port=configured_port or 443,
                logger=self.logger,
                protocol=protocol,
                tls_verify=tls_verify,
            )
        else:  # isilon
            self.client = IsilonClient(
                hostname=hostname,
                username=username,
                password=password,
                port=configured_port or 8080,
                logger=self.logger,
                protocol=protocol,
                tls_verify=tls_verify,
            )

        port = configured_port or (443 if self.storage_type == 'netapp' else 8080)
        self.logger.info(f"{self._log_prefix} Client initialized: {hostname}:{port}")

    def cleanup(self):
        """清理资源"""
        if self.client:
            self.client.close()

    # ------------------------------------------------------------------
    # 数据采集主流程
    # ------------------------------------------------------------------

    def execute_data_collection(self, include_questdb=True):
        """执行数据采集流程"""
        capacity_pools = self.fetch_capacity_pools()
        raw_isilon_quotas = self.client.get_quotas() if self.storage_type == 'isilon' else None
        storage_spaces = (
            self._isilon_directory_quota_spaces(raw_isilon_quotas)
            if self.storage_type == 'isilon'
            else self.fetch_storage_spaces()
        )

        self.sync_data_to_postgres(
            capacity_pools,
            Aggregate,
            ['name', 'storage_cluster_id'],
            delete_redundant=True,
        )
        self.sync_data_to_postgres(
            storage_spaces,
            Volume,
            ['name', 'storage_cluster_id'],
            delete_redundant=True,
        )

        if self.storage_type == 'netapp':
            qtrees = self.fetch_qtrees()
            self.sync_data_to_postgres(
                qtrees,
                Qtree,
                ['name', 'volume_id', 'storage_cluster_id'],
                delete_redundant=True,
            )
            self.migrate_null_qtree_bindings()
            self.calculate_volume_allocation()

        user_quotas = self.fetch_user_quotas(raw_isilon_quotas)
        self.sync_data_to_postgres(user_quotas, StorageUsage, ['group_id', 'user_id','storage_cluster_id'],
                                    exclude_keys=['group_id', 'user_id','storage_cluster_id'])

        self.aggregate_group_usage()
        self.aggregate_cluster_usage(include_questdb=False)
        if include_questdb:
            self.write_questdb()

    # ------------------------------------------------------------------
    # 数据获取方法
    # ------------------------------------------------------------------

    def fetch_capacity_pools(self) -> List[aggregateSchema.AggregateBase]:
        """获取容量池信息。"""
        result = []
        if self.client is None:
            return result

        records = (
            self.client.get_aggregates()
            if self.storage_type == 'netapp'
            else self.client.get_storage_pools()
        )
        for rec in records:
            if self.storage_type == 'netapp':
                space = rec.get('space', {}).get('block_storage', {})
                total = _bytes_to_gb(space.get('size'))
                available = _bytes_to_gb(space.get('available'))
                used = round(total - available, 2) if total is not None and available is not None else None
            else:
                usage = rec.get('usage')
                if not isinstance(usage, dict):
                    raise ValueError('Invalid Isilon storage pool record')
                total = _bytes_to_gb(usage.get('total_bytes'))
                used = _bytes_to_gb(usage.get('used_bytes'))
            if not rec.get('name') or total is None or used is None:
                if self.storage_type == 'isilon':
                    raise ValueError('Invalid Isilon storage pool record')
                continue
            result.append(aggregateSchema.AggregateBase(
                storage_cluster_id=self.storage_cluster_id,
                name=rec['name'],
                limit=total,
                used=used,
                use_ratio=round(used * 100 / total, 2) if total else 0,
                updated_at=datetime.now(),
            ))
        self.logger.info(f"{self._log_prefix} Fetched {len(result)} capacity pools")
        return result

    def fetch_storage_spaces(self) -> List[volumeSchema.VolumeBase]:
        """获取 NetApp 存储空间信息。"""
        result = []
        if self.client is None:
            return result

        for rec in self.client.get_volumes():
            space = rec.get('space', {})
            total = _bytes_to_gb(space.get('size'))
            available = _bytes_to_gb(space.get('available'))
            if not rec.get('name') or total is None or available is None:
                continue
            used = round(total - available, 2)
            agg_list = rec.get('aggregates', [])
            result.append(volumeSchema.VolumeBase(
                storage_cluster_id=self.storage_cluster_id,
                name=rec['name'],
                vserver=rec.get('svm', {}).get('name', ''),
                state=rec.get('state', ''),
                type=rec.get('type', ''),
                aggregate=agg_list[0].get('name', '') if agg_list else '',
                limit=total,
                used=used,
                use_ratio=round(used * 100 / total, 2) if total else 0,
                updated_at=datetime.now(),
            ))
        self.logger.info(f"{self._log_prefix} Fetched {len(result)} storage spaces")
        return result

    def fetch_qtrees(self) -> List[qtreeSchema.QtreeBase]:
        """获取 qtree 信息"""
        result = []
        if self.client is None:
            return result
        
        if self.storage_type == 'isilon':
            return result  # Isilon 不支持 qtree
        
        volumes_map = {
            vol.name: vol.id
            for vol in self.db.query(Volume).filter(
                Volume.storage_cluster_id == self.storage_cluster_id
            )
        }
        for rec in self.client.get_qtrees() or []:
            volume_id = volumes_map.get(rec.get('volume', {}).get('name', ''))
            name = rec.get('name', '')
            if volume_id is None or not name:
                continue
            result.append(qtreeSchema.QtreeBase(
                storage_cluster_id=self.storage_cluster_id,
                name=name,
                volume_id=volume_id,
                style=rec.get('security_style', ''),
                oplocks=str(rec.get('oplocks', {}).get('enabled', False)),
                status=rec.get('statistics', {}).get('status', ''),
                updated_at=datetime.now(),
            ))
        self.logger.info(f"{self._log_prefix} Fetched {len(result)} qtrees")
        return result

    def fetch_user_quotas(self, raw_isilon_quotas=None) -> list[StorageUsageBase]:
        """获取用户配额使用情况"""
        group_dbs = self.db.query(Group).filter(
            Group.enable_monitoring.is_(True),
            Group.storage_cluster_id == self.storage_cluster_id).all()
        group_map: Dict[tuple[str, int], List] = {}
        for g in group_dbs:
            target_key = (
                ('qtree', g.qtree_id)
                if g.qtree_id is not None
                else ('volume', g.volume_id)
            )
            if target_key[1] is not None:
                group_map.setdefault(target_key, []).append(g)

        users = self.db.query(User).all()
        users_map = {u.rd_username: u.id for u in users if u}
        users_uid_map = {str(u.uid): u for u in users}

        su_dbs = self.db.query(StorageUsage).join(Group, StorageUsage.group_id == Group.id).filter(
            Group.associate_multiple_groups.is_(True),
            StorageUsage.storage_cluster_id == self.storage_cluster_id).all()
        storage_usage_map = {
            (
                su.user_id,
                'qtree' if su.group.qtree_id is not None else 'volume',
                su.group.qtree_id if su.group.qtree_id is not None else su.group.volume_id,
            ): su
            for su in su_dbs if su.group
        }
        if self.storage_type == 'netapp':
            qtree_volume_dbs = self.db.query(Qtree, Volume.name).join(
                Volume, Qtree.volume_id == Volume.id).filter(
                Qtree.storage_cluster_id == self.storage_cluster_id).all()
            target_map = {
                (volume_name, qtree.name): ('qtree', qtree)
                for qtree, volume_name in qtree_volume_dbs
            }
            target_map.update({
                (volume.name, None): ('volume', volume)
                for volume in self.db.query(Volume).filter(
                    Volume.storage_cluster_id == self.storage_cluster_id
                )
            })
            return self._fetch_user_quotas_netapp(
                target_map, group_map, users_map, users_uid_map, storage_usage_map
            )

        target_map = {
            volume.name: volume
            for volume in self.db.query(Volume).filter(
                Volume.storage_cluster_id == self.storage_cluster_id
            )
        }
        _, quotas = self._fetch_user_quotas_isilon(
            target_map,
            group_map,
            users_map,
            users_uid_map,
            storage_usage_map,
            raw_quotas=raw_isilon_quotas,
        )
        return quotas

    def _fetch_user_quotas_netapp(self, target_map, group_map,
                        users_map, users_uid_map, storage_usage_map) -> List[storageUsageSchema.StorageUsageBase]:
        """NetApp 用户配额获取"""
        result = []
        if self.client is None:
            return result
        records = self.client.get_quota_reports()
        for rec in records:
            quota_type = rec.get('type', '')
            if quota_type == 'user':
                item = self._process_quota_user_netapp(
                    rec, target_map, group_map,
                    users_map, users_uid_map, storage_usage_map
                )
                if item:
                    result.append(item)
            elif quota_type == 'tree':
                vol_name = rec.get('volume', {}).get('name', '')
                qtree_name = rec.get('qtree', {}).get('name') or None
                resolved = target_map.get((vol_name, qtree_name))
                if resolved:
                    target = resolved[1] if isinstance(resolved, tuple) else resolved
                    space = rec.get('space', {})
                    used = _bytes_to_gb(space.get('used'))
                    limit = _quota_limit_to_gb(space.get('hard_limit'))
                    soft_limit = _quota_limit_to_gb(space.get('soft_limit'))
                    target.limit = limit
                    target.soft_limit = soft_limit
                    target.used = used
                    target.use_ratio = _calculate_use_ratio(used, limit)
                    target.soft_use_ratio = _calculate_use_ratio(used, soft_limit)
                    self.db.flush()

        self.logger.info(f"{self._log_prefix} Fetched {len(result)} user quotas")
        return result

    def migrate_null_qtree_bindings(self):
        """把历史虚拟 null Qtree 绑定迁移到其 Volume。"""
        null_qtrees = self.db.query(Qtree).filter(
            Qtree.name == 'null',
            Qtree.storage_cluster_id == self.storage_cluster_id,
        ).all()
        for qtree in null_qtrees:
            self.db.query(Group).filter(Group.qtree_id == qtree.id).update(
                {Group.volume_id: qtree.volume_id, Group.qtree_id: None},
                synchronize_session=False,
            )
            self.db.delete(qtree)
        self.db.flush()
        self.logger.info(
            f"{self._log_prefix} Migrated {len(null_qtrees)} null qtree bindings"
        )

    # ------------------------------------------------------------------
    # 数据聚合计算方法
    # ------------------------------------------------------------------

    def calculate_volume_allocation(self):
        """计算 volume 已分配给 qtree 的容量"""
        if self.storage_type == 'isilon':
            return  # Isilon 无 qtree

        volume_dbs = self.db.query(Volume).filter(
            Volume.storage_cluster_id == self.storage_cluster_id).all()
        for volume_db in volume_dbs:
            qtree_sum = self.db.query(func.sum(Qtree.limit)).filter(
                Qtree.volume_id == volume_db.id,
            ).scalar()
            volume_db.allocated = qtree_sum if qtree_sum else volume_db.limit
            self.db.flush()
        self.logger.info(f"{self._log_prefix} Calculated allocation for {len(volume_dbs)} volumes")

    def aggregate_group_usage(self):
        """聚合计算组的存储使用量"""
        direct_groups = []
        for target_model, target_id in (
            (Volume, Group.volume_id),
            (Qtree, Group.qtree_id),
        ):
            rows = self.db.query(Group, target_model).join(
                target_model, target_model.id == target_id
            ).filter(
                Group.enable_monitoring.is_(True),
                Group.associate_multiple_groups.is_(False),
                Group.storage_cluster_id == self.storage_cluster_id,
            ).all()
            direct_groups.extend(rows)
            for group, target in rows:
                self._apply_group_update(group.id, {
                    "limit": target.limit,
                    "soft_limit": target.soft_limit,
                    "used": target.used,
                    "use_ratio": target.use_ratio,
                    "soft_use_ratio": target.soft_use_ratio,
                    "updated_at": datetime.now(),
                })

        grouped_usage = self.db.query(
            Group.id,
            func.sum(StorageUsage.used),
            func.sum(StorageUsage.limit),
            func.sum(StorageUsage.soft_limit),
        ).outerjoin(
            StorageUsage,
            (StorageUsage.group_id == Group.id)
            & (StorageUsage.storage_cluster_id == self.storage_cluster_id),
        ).filter(
            Group.enable_monitoring.is_(True),
            Group.associate_multiple_groups.is_(True),
            Group.storage_cluster_id == self.storage_cluster_id,
        ).group_by(Group.id).all()
        for group_id, used, limit, soft_limit in grouped_usage:
            used = used or 0
            limit = limit or 0
            self._apply_group_update(group_id, {
                "used": used,
                "limit": limit,
                "soft_limit": soft_limit,
                "use_ratio": round(used * 100 / limit, 2) if limit else 0,
                "soft_use_ratio": _calculate_use_ratio(used, soft_limit),
                "updated_at": datetime.now(),
            })

        self.logger.info(
            f"{self._log_prefix} Aggregated usage for "
            f"{len(direct_groups) + len(grouped_usage)} groups"
        )

    def _apply_group_update(self, group_id, values):
        snapshot = self.group_snapshots.get(group_id)
        if snapshot is None:
            return False
        result = self.db.execute(
            update(Group)
            .where(
                Group.id == group_id,
                Group.project_id == snapshot["project_id"],
                Group.storage_cluster_id == snapshot["storage_cluster_id"],
                Group.group_tag_id == snapshot["group_tag_id"],
                Group.enable_monitoring.is_(True),
            )
            .values(**values)
        )
        return result.rowcount > 0

    def aggregate_cluster_usage(self, include_questdb=True):
        """汇总集群容量，更新 PostgreSQL 并按需写入 QuestDB。"""
        try:
            if self.storage_type == 'isilon':
                stats = self.client.get_cluster_stats()
                if not isinstance(stats, dict):
                    raise ValueError("Invalid OneFS cluster statfs response")
                block_size = stats.get('f_bsize', 512)
                total_limit = _bytes_to_gb(stats.get('f_blocks', 0) * block_size)
                available = _bytes_to_gb(stats.get('f_bavail', 0) * block_size)
                if total_limit is None or available is None:
                    raise ValueError("Invalid OneFS cluster statfs capacity")
                total_used = round(total_limit - available, 2)
            else:
                result = self.db.query(
                    func.sum(Aggregate.used), func.sum(Aggregate.limit)
                ).filter(
                    Aggregate.storage_cluster_id == self.storage_cluster_id
                ).first()
                total_used = result[0] if result[0] is not None else 0
                total_limit = result[1] if result[1] is not None else 0
            use_ratio = round(total_used * 100 / total_limit, 2) if total_limit > 0 else 0

            # 更新 PostgreSQL StorageCluster
            self.storage_cluster.used = total_used
            self.storage_cluster.limit = total_limit
            self.storage_cluster.use_ratio = use_ratio
            self.storage_cluster.updated_at = datetime.now()
            self.db.flush()

            if include_questdb:
                self.insert_metrics_to_questdb('storage_cluster', [self.storage_cluster])

            self.logger.info(
                f"{self._log_prefix} Aggregated cluster usage: "
                f"used={total_used} GB, limit={total_limit} GB, ratio={use_ratio}%"
            )
        except SQLAlchemyError as e:
            self.logger.error(f"{self._log_prefix} Failed to aggregate cluster usage: {e}")
            raise



    def insert_metrics_to_questdb(self, table_name: str, items: List):
        """插入时序指标数据到 QuestDB"""
        if not items:
            return
        try:
            if table_name == 'storage_cluster':
                # StorageCluster 聚合数据写入 storage_cluster_storage_usages
                data = [
                    {'storage_cluster_id': str(item.id), 'used': item.used,
                     'use_ratio': item.use_ratio, 'updated_at': datetime.now()}
                    for item in items if item.used is not None
                ]
                table_name = 'storage_cluster_storage_usages'
            elif table_name != 'storage_usages':
                data = []
                for item in items:
                    if not item.used:
                        continue
                    row = {
                        'used': item.used,
                        'used_ratio': item.use_ratio,
                        f'{table_name}_id': str(item.id),
                        'updated_at': datetime.now(),
                    }
                    if hasattr(item, 'soft_limit'):
                        row.update(
                            soft_limit=item.soft_limit,
                            soft_use_ratio=item.soft_use_ratio,
                        )
                    data.append(row)
                table_name = f"{table_name}_storage_usages"
            else:
                data = [
                    {'used': item.used, 'used_ratio': item.use_ratio, 'file_used': item.file_used,
                     'soft_limit': item.soft_limit, 'soft_use_ratio': item.soft_use_ratio,
                     f'{table_name[:-1]}_id': str(item.id), 'updated_at': item.updated_at,
                     'user_id': str(item.user_id)}
                    for item in items if item.used
                ]
            if not data:
                return
            with QuestDBSession() as conn:
                trans = conn.begin()
                keys = ', '.join(data[0].keys())
                placeholders = ', '.join([f":{k}" for k in data[0].keys()])
                insert_command = text(
                    f"INSERT BATCH {len(data)} INTO {table_name} ({keys}) VALUES ({placeholders});"
                )
                conn.execute(insert_command, data)
                trans.commit()
            self.logger.info(f"{self._log_prefix} Inserted {len(data)} metric records to QuestDB [{table_name}]")
        except Exception as e:
            self.logger.error(f"{self._log_prefix} Failed to insert metrics to QuestDB [{table_name}]: {e}")

    # ------------------------------------------------------------------
    # 数据同步方法
    # ------------------------------------------------------------------

    def sync_data_to_postgres(self, data: List, model, unique_keys: List[str],
                              exclude_keys=None, delete_redundant: bool = False):
        """同步数据到 PostgreSQL"""
        if exclude_keys is None:
            exclude_keys = []
        if not data:
            return False
        try:
            existing_data = self.db.query(model).filter(
                model.storage_cluster_id == self.storage_cluster_id).all()
            existing_data_map = {
                tuple(getattr(item, key) for key in unique_keys): item
                for item in existing_data
            }
            new_data = []
            for item in data:
                item_key = tuple(getattr(item, key) for key in unique_keys)
                item_db = existing_data_map.get(item_key)
                if item_db is None:
                    item_dict = item.model_dump()
                    # item_dict['storage_cluster_id'] = self.storage_cluster_id
                    new_data.append(model(**item_dict))
                else:
                    for key, value in item.model_dump(exclude=set(exclude_keys)).items():
                        setattr(item_db, key, value)
                    self.db.merge(item_db)
            if new_data:
                self.db.add_all(new_data)

            if delete_redundant:
                data_keys = {tuple(getattr(item, key) for key in unique_keys) for item in data}
                extra_data = [item for key, item in existing_data_map.items() if key not in data_keys]
                if extra_data:
                    deleted = 0
                    for item in extra_data:
                        if model is Volume and (
                            self.db.query(Group).filter(Group.volume_id == item.id).first()
                            or self.db.query(Qtree).filter(Qtree.volume_id == item.id).first()
                        ):
                            self.logger.warning(
                                f"{self._log_prefix} Preserved referenced storage space {item.id}"
                            )
                            continue
                        if model is Qtree and self.db.query(Group).filter(
                            Group.qtree_id == item.id
                        ).first():
                            self.logger.warning(
                                f"{self._log_prefix} Preserved referenced qtree {item.id}"
                            )
                            continue
                        self.db.delete(item)
                        deleted += 1
                    self.logger.info(
                        f"{self._log_prefix} Deleted {deleted} redundant {model.__name__} records"
                    )

            self.db.flush()
            self.logger.info(f"{self._log_prefix} Synced {len(data)} {model.__name__} records to PostgreSQL")
            return True
        except SQLAlchemyError as e:
            self.logger.error(f"{self._log_prefix} Failed to sync {model.__name__} to PostgreSQL: {e}")
            raise

    def _process_quota_user_isilon(self, record: Dict, target_map: Dict, group_map: Dict,
                                    users_map: Dict, users_uid_map: Dict,
                                    storage_usage_map: Dict) -> Optional[storageUsageSchema.StorageUsageBase]:
        """处理 isilon 用户配额记录"""
        try:
            vol_name = record.get('path')
            target = target_map.get(vol_name)
            if target is None:
                return None
            rd_username = record.get('rd_username', '').strip()
            limit = record.get('limit')
            soft_limit = record.get('soft_limit')
            used = record.get('used')
            use_ratio = record.get('use_ratio')
            soft_use_ratio = record.get('soft_use_ratio')
            target_id = target.id
            # 判断用户名是否为数字 为数字证明离职
            if rd_username.isdigit():
                user = users_uid_map.get(rd_username)
                if not user:
                    return None
                user_id = user.id
                rd_username = user.rd_username
            else:
                user_id = users_map.get(rd_username)
                if not user_id:
                    new_user = User(rd_username=rd_username, updated_at=datetime.now())
                    self.db.add(new_user)
                    self.db.flush()
                    user_id = new_user.id
                    users_map[rd_username] = user_id
            group_dbs = group_map.get(
                ('volume', target_id),
                group_map.get(target_id),
            )
            if not group_dbs:
                return None
            elif len(group_dbs) == 1:
                group_db = group_dbs[0]
            else:
                group_db = group_dbs[0]

            if group_db and group_db.associate_multiple_groups is False:
                group_id = group_db.id
            else:
                su_db = storage_usage_map.get(
                    (user_id, 'volume', target_id),
                    storage_usage_map.get((user_id, target_id)),
                )
                if su_db is None:
                    return None
                group_db = su_db.group
                group_id = su_db.group_id

            if user_id and group_id:
                linux_path = f"{group_db.linux_path}/{rd_username}".replace('//', '/')
                return storageUsageSchema.StorageUsageBase(
                    storage_cluster_id=self.storage_cluster_id,
                    user_id=user_id, group_id=group_id, limit=limit, soft_limit=soft_limit, used=used,
                    use_ratio=use_ratio, soft_use_ratio=soft_use_ratio, file_used=0, linux_path=linux_path,
                    file_limit=0, updated_at=datetime.now()
                )
        except Exception as e:
            self.logger.error(f"{self._log_prefix} Failed to process quota user record: {e}")
        return None

    def _process_quota_user_netapp(self, record: Dict, target_map: Dict, group_map: Dict,
                                    users_map: Dict, users_uid_map: Dict,
                                    storage_usage_map: Dict) -> Optional[storageUsageSchema.StorageUsageBase]:
        """处理 netapp 用户配额记录"""
        try:
            vol_name = record.get('volume', {}).get('name', '')
            qtree_name = record.get('qtree', {}).get('name') or None
            resolved = target_map.get((vol_name, qtree_name))
            if resolved is None:
                return None
            if isinstance(resolved, tuple):
                target_type, target = resolved
            else:
                target_type, target = 'qtree', resolved

            users_list = record.get('users', [])
            if not users_list:
                return None
            user_entry = users_list[0]
            rd_username = user_entry.get('name', '').strip()
            if rd_username in ('*', 'root', ''):
                return None

            space = record.get('space', {})
            used_info = space.get('used', {})
            used = _bytes_to_gb(used_info.get('total')) or 0
            limit = _quota_limit_to_gb(space.get('hard_limit'))
            soft_limit = _quota_limit_to_gb(space.get('soft_limit'))
            use_ratio = _calculate_use_ratio(used, limit)
            soft_use_ratio = _calculate_use_ratio(used, soft_limit)

            files_rec = record.get('files', {})
            file_used_raw = files_rec.get('used', {})
            file_used = file_used_raw.get('total', 0) if isinstance(file_used_raw, dict) else 0
            file_limit = files_rec.get('hard_limit')


            target_id = target.id
            # 判断用户名是否为数字 为数字证明离职
            if rd_username.isdigit():
                user = users_uid_map.get(rd_username)
                if not user:
                    return None
                user_id = user.id
                rd_username = user.rd_username
            else:
                user_id = users_map.get(rd_username)
                if not user_id:
                    new_user = User(rd_username=rd_username, updated_at=datetime.now())
                    self.db.add(new_user)
                    self.db.flush()
                    user_id = new_user.id
                    users_map[rd_username] = user_id

            group_dbs = group_map.get(
                (target_type, target_id),
                group_map.get(target_id),
            )
            if not group_dbs or len(group_dbs) > 1:
                group_db = None
            else:
                group_db = group_dbs[0]

            if group_db and group_db.associate_multiple_groups is False:
                group_id = group_db.id
            else:
                su_db = storage_usage_map.get(
                    (user_id, target_type, target_id),
                    storage_usage_map.get((user_id, target_id)),
                )
                if su_db is None:
                    return None
                group_db = su_db.group
                group_id = su_db.group_id

            if user_id and group_id:
                linux_path = f"{group_db.linux_path}/{rd_username}".replace('//', '/')
                return storageUsageSchema.StorageUsageBase(
                    storage_cluster_id=self.storage_cluster_id,
                    user_id=user_id, group_id=group_id, limit=limit, soft_limit=soft_limit, used=used,
                    use_ratio=use_ratio, soft_use_ratio=soft_use_ratio, file_used=file_used, linux_path=linux_path,
                    file_limit=file_limit, updated_at=datetime.now()
                )
        except Exception as e:
            self.logger.error(f"{self._log_prefix} Failed to process quota user record: {e}")
        return None


    def _isilon_directory_quota_spaces(self, raw_quotas):
        spaces = []
        for quota in raw_quotas:
            if quota.get('type') != 'directory' or not quota.get('path'):
                continue
            thresholds = quota.get('thresholds', {})
            used = _bytes_to_gb(quota.get('usage', {}).get('logical'))
            limit = _bytes_to_gb(thresholds.get('hard'))
            soft_limit = _quota_limit_to_gb(thresholds.get('soft'))
            spaces.append(volumeSchema.VolumeBase(
                storage_cluster_id=self.storage_cluster_id,
                name=quota['path'],
                vserver='',
                state='',
                type='directory_quota',
                allocated=limit,
                aggregate='',
                limit=limit,
                soft_limit=soft_limit,
                used=used,
                use_ratio=_calculate_use_ratio(used, limit),
                soft_use_ratio=_calculate_use_ratio(used, soft_limit),
                updated_at=datetime.now(),
            ))
        return spaces

    def _fetch_user_quotas_isilon(self, target_map, group_map,
                        users_map, users_uid_map, storage_usage_map,
                        raw_quotas=None) -> tuple[list[VolumeBase], list[StorageUsageBase]]:
        """Isilon 用户配额获取"""
        volumes = []
        quotas = []
        if self.client is None:
            return volumes, quotas
        raw_quotas = self.client.get_quotas() if raw_quotas is None else raw_quotas
        volumes = self._isilon_directory_quota_spaces(raw_quotas)
        default_user_quotas_map = {}
        user_quotas = []
        for quota in raw_quotas:
            quota_type = quota.get('type')
            thresholds = quota.get('thresholds', {})
            path = quota.get('path')
            hard_limit = _bytes_to_gb(thresholds.get('hard'))
            soft_limit = _quota_limit_to_gb(thresholds.get('soft'))
            if quota_type == 'default-user':
                default_user_quotas_map[path] = (hard_limit, soft_limit)
            elif quota_type == 'user':
                rd_username = (quota.get('persona') or {}).get('name', '').strip()
                if rd_username in ('*', 'root', ''):
                    continue
                user_quotas.append({
                    'path': path,
                    'linked': quota.get('linked', False),
                    'used': _bytes_to_gb(quota.get('usage', {}).get('logical')),
                    'hard_limit': hard_limit,
                    'soft_limit': soft_limit,
                    'rd_username': rd_username,
                })

        for quota in user_quotas:
            limit = quota['hard_limit']
            soft_limit = quota['soft_limit']
            if quota['linked']:
                limit, soft_limit = default_user_quotas_map.get(
                    quota['path'],
                    (None, None),
                )
            quota.update(
                limit=limit,
                soft_limit=soft_limit,
                use_ratio=_calculate_use_ratio(quota['used'], limit),
                soft_use_ratio=_calculate_use_ratio(quota['used'], soft_limit),
            )
            item = self._process_quota_user_isilon(
                quota, target_map, group_map,
                users_map, users_uid_map, storage_usage_map
            )
            if item:
                quotas.append(item)

        self.logger.info(
            f"{self._log_prefix} Fetched {len(quotas)} user quotas "
            f"{len(volumes)} storage spaces"
        )
        return volumes, quotas
