# -*- coding: utf-8 -*-
from datetime import datetime
from crud.configCrud import get_storage_config
from sqlalchemy.exc import SQLAlchemyError

from schemas.storageUsageSchema import StorageUsageBase
from schemas.volumeSchema import VolumeBase
from utils.netAppClient import NetAppClient
from utils.isilonClient import IsilonClient
from schemas import aggregateSchema, volumeSchema, qtreeSchema, storageUsageSchema
from models import Aggregate, Volume, Qtree, Group, StorageUsage, User, Project, StorageCluster
from sqlalchemy import func, text
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

    def __init__(self, db, logger, storage_cluster_id: int):
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
        self.storage_cluster: StorageCluster = db.query(StorageCluster).filter_by(
            id=storage_cluster_id).first()
        if self.storage_cluster is None:
            raise ValueError(f"StorageCluster with id={storage_cluster_id} not found")
        self.storage_type = self.storage_cluster.storage_type.lower()
        self.config = None   # 全局配置（QuestDB 等），在 setup() 中加载
        self.client = None

        if self.storage_type not in ('netapp', 'isilon'):
            raise ValueError(f"Unsupported storage type: {self.storage_type}")

    @property
    def _log_prefix(self):
        """日志前缀"""
        type_name = 'NetApp' if self.storage_type == 'netapp' else 'Isilon'
        return f"[StoragePulse|{type_name}|{self.storage_cluster.name}]"

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def start(self):
        """启动监控流程"""
        self.setup()
        self.execute_data_collection()
        self.cleanup()

    def setup(self):
        """初始化客户端连接"""
        # 全局配置仅用于 QuestDB 连接
        self.config = get_storage_config(db=self.db)

        cluster = self.storage_cluster
        if self.storage_type == 'netapp':
            self.client = NetAppClient(
                hostname=cluster.storage_host,
                username=cluster.storage_user,
                password=cluster.storage_password,
                port=cluster.storage_port or 443,
                logger=self.logger
            )
        else:  # isilon
            self.client = IsilonClient(
                hostname=cluster.storage_host,
                username=cluster.storage_user,
                password=cluster.storage_password,
                port=cluster.storage_port or 8080,
                logger=self.logger
            )

        port = cluster.storage_port or (443 if self.storage_type == 'netapp' else 8080)
        self.logger.info(f"{self._log_prefix} Client initialized: {cluster.storage_host}:{port}")

    def cleanup(self):
        """清理资源"""
        if self.client:
            self.client.close()
        self.db.commit()

    # ------------------------------------------------------------------
    # 数据采集主流程
    # ------------------------------------------------------------------

    def execute_data_collection(self):
        """执行数据采集流程"""
        aggregates = self.fetch_aggregates()

        volumes, user_quotas = self.fetch_user_quotas()
        
        self.sync_data_to_postgres(aggregates, Aggregate, ['name','storage_cluster_id'])
        self.sync_data_to_postgres(volumes, Volume, ['name','storage_cluster_id'], delete_redundant=True)
        
        # Isilon: 为每个 volume 创建 null qtree；NetApp: 从 API 获取 qtrees
        if self.storage_type == 'isilon':
            qtrees = self._create_null_qtrees_for_volumes()
        else:
            qtrees = self.fetch_qtrees()
        
        self.sync_data_to_postgres(qtrees, Qtree, ['name', 'volume_id','storage_cluster_id'], delete_redundant=True)
        self.update_null_qtree_from_volume()
        self.calculate_volume_allocation()

        self.sync_data_to_postgres(user_quotas, StorageUsage, ['group_id', 'user_id','storage_cluster_id'],
                                    exclude_keys=['group_id', 'user_id','storage_cluster_id'])

        self.aggregate_group_usage()
        self.aggregate_project_usage()
        self.aggregate_cluster_usage()

        self.insert_metrics_to_questdb('storage_usages', self.db.query(StorageUsage).filter(
            StorageUsage.used > 0, StorageUsage.storage_cluster_id == self.storage_cluster_id).all())
        self.insert_metrics_to_questdb('qtree', self.db.query(Qtree).filter(
            Qtree.used >= 0, Qtree.storage_cluster_id == self.storage_cluster_id).all())
        self.insert_metrics_to_questdb('volume', self.db.query(Volume).filter(
            Volume.used >= 0, Volume.storage_cluster_id == self.storage_cluster_id).all())
        self.insert_metrics_to_questdb('project', self.db.query(Project).filter(Project.used >= 0).all())
        # Isilon 没有 qtree，不过滤 qtree_id；NetApp 需要 qtree_id 不为空
        group_query = self.db.query(Group).filter(
            Group.enable_monitoring.is_(True),
            Group.storage_cluster_id == self.storage_cluster_id)
        if self.storage_type == 'netapp':
            group_query = group_query.filter(Group.qtree_id.isnot(None))
        self.insert_metrics_to_questdb('group', group_query.all())
        self.insert_metrics_to_questdb('aggregate', self.db.query(Aggregate).filter(
            Aggregate.used >= 0, Aggregate.storage_cluster_id == self.storage_cluster_id).all())

    # ------------------------------------------------------------------
    # 数据获取方法
    # ------------------------------------------------------------------

    def fetch_aggregates(self) -> List[aggregateSchema.AggregateBase]:
        """获取聚合存储信息"""
        result = []
        if self.client is None:
            return result
        
        try:
            if self.storage_type == 'netapp':
                records = self.client.get_aggregates()
                for rec in records:
                    space = rec.get('space', {})
                    total = _bytes_to_gb(space.get('block_storage', {}).get('size'))
                    available = _bytes_to_gb(space.get('block_storage', ).get('available'))
                    if total is None or available is None:
                        continue
                    used = round(total - available, 2)
                    use_ratio = round(used * 100 / total, 2) if total else 0
                    result.append(aggregateSchema.AggregateBase(
                        storage_cluster_id=self.storage_cluster_id,
                        name=rec.get('name', ''),
                        limit=total,
                        used=used,
                        use_ratio=use_ratio,
                        updated_at=datetime.now()
                    ))
            else:  # isilon
                stats = self.client.get_cluster_stats()
                if stats:
                    bsize = stats.get('f_bsize', 512)
                    total = _bytes_to_gb(stats.get('f_blocks', 0) * bsize)
                    available = _bytes_to_gb(stats.get('f_bavail', 0) * bsize)
                    if total is not None and available is not None:
                        used = round(total - available, 2)
                        use_ratio = round(used * 100 / total, 2) if total else 0
                        result.append(aggregateSchema.AggregateBase(
                            storage_cluster_id=self.storage_cluster_id,
                            name='isilon_cluster',
                            limit=total,
                            used=used,
                            use_ratio=use_ratio,
                            updated_at=datetime.now()
                        ))
            self.logger.info(f"{self._log_prefix} Fetched {len(result)} aggregates")
        except Exception as e:
            self.logger.error(f"{self._log_prefix} Failed to fetch aggregates: {e}")
        return result

    def fetch_volumes(self) -> List[volumeSchema.VolumeBase]:
        """获取卷信息"""
        result = []
        if self.client is None:
            return result
        
        try:
            if self.storage_type == 'netapp':
                records = self.client.get_volumes()
                for rec in records:
                    space = rec.get('space', {})
                    total = _bytes_to_gb(space.get('size'))
                    available = _bytes_to_gb(space.get('available'))
                    if total is None or available is None:
                        continue
                    used = round(total - available, 2)
                    use_ratio = round(used * 100 / total, 2) if total else 0
                    svm = rec.get('svm', {})
                    agg_list = rec.get('aggregates', [])
                    agg_name = agg_list[0].get('name', '') if agg_list else ''
                    result.append(volumeSchema.VolumeBase(
                        storage_cluster_id=self.storage_cluster_id,
                        name=rec.get('name', ''),
                        vserver=svm.get('name', ''),
                        state=rec.get('state', ''),
                        type=rec.get('type', ''),
                        aggregate=agg_name,
                        limit=total,
                        used=used,
                        use_ratio=use_ratio,
                        updated_at=datetime.now()
                    ))
            else:  # isilon
                pass
            self.logger.info(f"{self._log_prefix} Fetched {len(result)} volumes")
        except Exception as e:
            self.logger.error(f"{self._log_prefix} Failed to fetch volumes: {e}")
        return result

    def _create_null_qtrees_for_volumes(self) -> List[qtreeSchema.QtreeBase]:
        """为 Isilon volumes 创建对应的 null qtrees"""
        result = []
        volumes = self.db.query(Volume).filter(
            Volume.storage_cluster_id == self.storage_cluster_id).all()
        
        for vol in volumes:
            result.append(qtreeSchema.QtreeBase(
                storage_cluster_id=self.storage_cluster_id,
                name='null',
                volume_id=vol.id,
                limit=vol.limit,
                soft_limit=vol.soft_limit,
                used=vol.used,
                use_ratio=vol.use_ratio,
                soft_use_ratio=vol.soft_use_ratio,
                style='',
                oplocks='',
                status='',
                updated_at=datetime.now()
            ))
        
        self.logger.info(f"{self._log_prefix} Created {len(result)} null qtrees for volumes")
        return result

    def fetch_qtrees(self) -> List[qtreeSchema.QtreeBase]:
        """获取 qtree 信息"""
        result = []
        if self.client is None:
            return result
        
        if self.storage_type == 'isilon':
            return result  # Isilon 不支持 qtree
        
        try:
            existing_volumes = self.db.query(Volume).filter(
                Volume.storage_cluster_id == self.storage_cluster_id).all()
            volumes_map = {vol.name: vol.id for vol in existing_volumes}
            volumes_with_qtrees = set()

            records = self.client.get_qtrees() or []
            for rec in records:
                volume_name = rec.get('volume', {}).get('name', '')
                volume_id = volumes_map.get(volume_name)
                if volume_id is None:
                    continue
                volumes_with_qtrees.add(volume_id)
                name = rec.get('name', '')
                if name == '':
                    name = 'null'
                result.append(qtreeSchema.QtreeBase(
                    storage_cluster_id=self.storage_cluster_id,
                    name=name,
                    volume_id=volume_id,
                    style=rec.get('security_style', ''),
                    oplocks=str(rec.get('oplocks', {}).get('enabled', False)),
                    status=rec.get('statistics', {}).get('status', ''),
                    updated_at=datetime.now()
                ))

            # 为没有 qtree 的 volume 创建 null qtree
            for vol in existing_volumes:
                if vol.id not in volumes_with_qtrees:
                    result.append(qtreeSchema.QtreeBase(
                        storage_cluster_id=self.storage_cluster_id,
                        name='null',
                        volume_id=vol.id,
                        limit=vol.limit,
                        soft_limit=vol.soft_limit,
                        used=vol.used,
                        use_ratio=vol.use_ratio,
                        soft_use_ratio=vol.soft_use_ratio,
                        style='',
                        oplocks='',
                        status='',
                        updated_at=datetime.now()
                    ))

            self.logger.info(f"{self._log_prefix} Fetched {len(result)} qtrees")
        except Exception as e:
            self.logger.error(f"{self._log_prefix} Failed to fetch qtrees: {e}")
        return result

    def fetch_user_quotas(self) -> tuple[list[VolumeBase], list[StorageUsageBase]]:
        """获取用户配额使用情况"""
        qtree_volume_dbs = self.db.query(Qtree, Volume.name).join(
            Volume, Qtree.volume_id == Volume.id).filter(
            Qtree.storage_cluster_id == self.storage_cluster_id).all()
        qtree_map = {(volume_name, qtree.name): qtree for qtree, volume_name in qtree_volume_dbs}

        group_dbs = self.db.query(Group).filter(
            Group.enable_monitoring.is_(True),
            Group.storage_cluster_id == self.storage_cluster_id).all()
        group_map: Dict[int, List] = {}
        for g in group_dbs:
            group_map.setdefault(g.qtree_id, []).append(g)

        users = self.db.query(User).all()
        users_map = {u.rd_username: u.id for u in users if u}
        users_uid_map = {str(u.uid): u for u in users}

        su_dbs = self.db.query(StorageUsage).join(Group, StorageUsage.group_id == Group.id).filter(
            Group.associate_multiple_groups.is_(True),
            StorageUsage.storage_cluster_id == self.storage_cluster_id).all()
        storage_usage_map = {
            (su.user_id, su.group.qtree.id): su
            for su in su_dbs if su.group and su.group.qtree
        }
        if self.storage_type == 'netapp':
            volumes = self.fetch_volumes()
            quotas = self._fetch_user_quotas_netapp(qtree_map, group_map,
                        users_map, users_uid_map, storage_usage_map)
            return volumes,quotas
        else:
            volumes, quotas = self._fetch_user_quotas_isilon(qtree_map, group_map,
                        users_map, users_uid_map, storage_usage_map)
            return volumes,quotas

    def _fetch_user_quotas_netapp(self,qtree_map, group_map,
                        users_map, users_uid_map, storage_usage_map) -> List[storageUsageSchema.StorageUsageBase]:
        """NetApp 用户配额获取"""
        result = []
        if self.client is None:
            return result
        try:
            records = self.client.get_quota_reports()
            for rec in records:
                quota_type = rec.get('type', '')
                if quota_type == 'user':
                    item = self._process_quota_user_netapp(
                        rec, qtree_map, group_map,
                        users_map, users_uid_map, storage_usage_map
                    )
                    if item:
                        result.append(item)
                elif quota_type == 'tree':
                    vol_name = rec.get('volume', {}).get('name', '')
                    qtree_name = rec.get('qtree', {}).get('name', '') or 'null'
                    qtree_db = qtree_map.get((vol_name, qtree_name))
                    if qtree_db:
                        space = rec.get('space', {})
                        used = _bytes_to_gb(space.get('used'))
                        limit = _quota_limit_to_gb(space.get('hard_limit'))
                        soft_limit = _quota_limit_to_gb(space.get('soft_limit'))
                        use_ratio = _calculate_use_ratio(used, limit)
                        soft_use_ratio = _calculate_use_ratio(used, soft_limit)
                        qtree_db.limit = limit
                        qtree_db.soft_limit = soft_limit
                        qtree_db.used = used
                        qtree_db.use_ratio = use_ratio
                        qtree_db.soft_use_ratio = soft_use_ratio
                        self.db.commit()
            
            self.logger.info(f"{self._log_prefix} Fetched {len(result)} user quotas")
        except Exception as e:
            self.logger.error(f"{self._log_prefix} Failed to fetch user quotas: {e}")
        return result

    # ------------------------------------------------------------------
    # 数据聚合计算方法
    # ------------------------------------------------------------------

    def update_null_qtree_from_volume(self):
        """更新 null qtree 的使用量，使其与 volume 保持一致"""
        if self.storage_type == 'isilon':
            return

        null_qtrees = self.db.query(Qtree, Volume).join(Volume, Qtree.volume_id == Volume.id).filter(
            Qtree.name == 'null',
            Qtree.storage_cluster_id == self.storage_cluster_id
        ).all()
        
        for qtree_db, volume_db in null_qtrees:
            qtree_db.limit = volume_db.limit
            qtree_db.soft_limit = volume_db.soft_limit
            qtree_db.used = volume_db.used
            qtree_db.use_ratio = volume_db.use_ratio
            qtree_db.soft_use_ratio = volume_db.soft_use_ratio
            qtree_db.updated_at = datetime.now()
        
        self.db.commit()
        self.logger.info(f"{self._log_prefix} Updated {len(null_qtrees)} null qtrees from volumes")

    def calculate_volume_allocation(self):
        """计算 volume 已分配给 qtree 的容量"""
        if self.storage_type == 'isilon':
            return  # Isilon 无 qtree

        volume_dbs = self.db.query(Volume).filter(
            Volume.storage_cluster_id == self.storage_cluster_id).all()
        for volume_db in volume_dbs:
            qtree_sum = self.db.query(func.sum(Qtree.limit)).filter(
                Qtree.volume_id == volume_db.id,
                Qtree.name != 'null',
                Qtree.used > 0
            ).scalar()
            volume_db.allocated = qtree_sum if qtree_sum else volume_db.limit
            self.db.commit()
        self.logger.info(f"{self._log_prefix} Calculated allocation for {len(volume_dbs)} volumes")

    def aggregate_group_usage(self):
        """聚合计算组的存储使用量"""
        if self.storage_type == 'netapp':
            self._aggregate_group_usage_netapp()
        else:
            self._aggregate_group_usage_isilon()

    def _aggregate_group_usage_netapp(self):
        """NetApp 组使用量聚合"""
        # case0: qtree_id 为空
        case0_dbs = self.db.query(Group).filter(
            Group.enable_monitoring.is_(True), Group.qtree_id.is_(None),
            Group.storage_cluster_id == self.storage_cluster_id).all()
        for group_db in case0_dbs:
            group_db.limit = 0
            group_db.soft_limit = None
            group_db.used = 0
            group_db.use_ratio = 0
            group_db.soft_use_ratio = None
            self.db.commit()

        # case1: 与 volume 直接关联（qtree name == 'null'）
        case1_dbs = self.db.query(Group, Qtree, Volume)\
            .join(Group, Qtree.id == Group.qtree_id)\
            .join(Volume, Qtree.volume_id == Volume.id)\
            .filter(
                Qtree.name == 'null',
                Group.associate_multiple_groups.is_(False),
                Group.enable_monitoring.is_(True),
                Group.qtree_id.isnot(None),
                Group.storage_cluster_id == self.storage_cluster_id
            ).all()
        for group_db, qtree_db, volume_db in case1_dbs:
            group_db.limit = volume_db.limit
            group_db.soft_limit = volume_db.soft_limit
            group_db.used = volume_db.used
            group_db.use_ratio = volume_db.use_ratio
            group_db.soft_use_ratio = volume_db.soft_use_ratio
            self.db.commit()

        # case2: 与 qtree 直接关联
        case2_dbs = self.db.query(Group, Qtree)\
            .join(Group, Qtree.id == Group.qtree_id)\
            .filter(
                Qtree.name != 'null',
                Group.associate_multiple_groups.is_(False),
                Group.enable_monitoring.is_(True),
                Group.qtree_id.isnot(None),
                Group.storage_cluster_id == self.storage_cluster_id
            ).all()
        for group_db, qtree_db in case2_dbs:
            group_db.limit = qtree_db.limit
            group_db.soft_limit = qtree_db.soft_limit
            group_db.used = qtree_db.used
            group_db.use_ratio = qtree_db.use_ratio
            group_db.soft_use_ratio = qtree_db.soft_use_ratio
            self.db.commit()

        # case3: 分组聚合计算
        case3_dbs = self.db.query(
            Group.id, func.sum(StorageUsage.used), func.sum(StorageUsage.limit), func.sum(StorageUsage.soft_limit)
        ).join(Group, StorageUsage.group_id == Group.id)\
            .filter(
                Group.associate_multiple_groups.is_(True),
                Group.enable_monitoring.is_(True),
                Group.qtree_id.isnot(None),
                Group.storage_cluster_id == self.storage_cluster_id
            ).group_by(Group.id).all()
        for group_id, sum_used, sum_limit, sum_soft_limit in case3_dbs:
            group_db = self.db.query(Group).filter_by(id=group_id).first()
            sum_used = sum_used if sum_used else 0
            sum_limit = sum_limit if sum_limit else 0
            soft_limit = sum_soft_limit if sum_soft_limit else None
            group_db.used = sum_used
            limit = group_db.limit if group_db.limit is not None else sum_limit
            use_ratio = round((sum_used * 100) / limit, 2) if limit > 0 else 0
            group_db.limit = limit
            group_db.soft_limit = soft_limit
            group_db.use_ratio = use_ratio
            group_db.soft_use_ratio = _calculate_use_ratio(sum_used, soft_limit)
            group_db.updated_at = datetime.now()
            self.db.commit()

        self.logger.info(f"{self._log_prefix} Aggregated usage for groups")

    def _aggregate_group_usage_isilon(self):
        """Isilon 组使用量聚合"""
        group_dbs = self.db.query(Group).filter(
            Group.enable_monitoring.is_(True),
            Group.storage_cluster_id == self.storage_cluster_id).all()
        for group_db in group_dbs:
            sum_result = self.db.query(
                func.sum(StorageUsage.used), func.sum(StorageUsage.limit), func.sum(StorageUsage.soft_limit)
            ).filter(StorageUsage.group_id == group_db.id,
                     StorageUsage.storage_cluster_id == self.storage_cluster_id).first()
            
            sum_used = sum_result[0] if sum_result[0] else 0
            sum_limit = sum_result[1] if sum_result[1] else 0
            sum_soft_limit = sum_result[2] if sum_result[2] else None
            


            limit = sum_limit
            use_ratio = round((sum_used * 100) / limit, 2) if limit > 0 else 0

            group_db.used = sum_used
            group_db.limit = limit
            group_db.soft_limit = sum_soft_limit
            group_db.use_ratio = use_ratio
            group_db.soft_use_ratio = _calculate_use_ratio(sum_used, sum_soft_limit)
            group_db.updated_at = datetime.now()
            self.db.commit()
        
        self.logger.info(f"{self._log_prefix} Aggregated usage for {len(group_dbs)} groups")

    def aggregate_project_usage(self):
        """聚合计算项目的存储使用量"""
        try:
            # 项目存储不需要做分类
            group_filter = [
                Group.enable_monitoring.is_(True),
                # Group.storage_cluster_id == self.storage_cluster_id,
            ]
            if self.storage_type == 'netapp':
                group_filter.append(Group.qtree_id.isnot(None))

            project_store_dbs = self.db.query(
                Group.project_id, func.sum(Group.used), func.sum(Group.limit), func.sum(Group.soft_limit)
            ).filter(*group_filter).group_by(Group.project_id).all()

            for project_id, used, limit, soft_limit in project_store_dbs:
                use_ratio = round((used * 100 / limit), 2) if limit else None
                soft_use_ratio = _calculate_use_ratio(used, soft_limit)
                self.db.query(Project).filter_by(id=project_id).update(
                    {'limit': limit, 'soft_limit': soft_limit, 'used': used,
                     'use_ratio': use_ratio, 'soft_use_ratio': soft_use_ratio,
                     'updated_at': datetime.now()}
                )
            self.db.commit()
            self.logger.info(f"{self._log_prefix} Aggregated usage for {len(project_store_dbs)} projects")
            return True
        except SQLAlchemyError as e:
            self.logger.error(f"{self._log_prefix} Failed to aggregate project usage: {e}")
            return False

    def aggregate_cluster_usage(self):
        """按 Aggregate 聚合计算 StorageCluster 的总使用量，更新 PostgreSQL 并写入 QuestDB"""
        try:
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
            self.db.commit()

            # 写入 QuestDB storage_cluster_storage_usages
            self.insert_metrics_to_questdb('storage_cluster', [self.storage_cluster])

            self.logger.info(
                f"{self._log_prefix} Aggregated cluster usage: "
                f"used={total_used} GB, limit={total_limit} GB, ratio={use_ratio}%"
            )
        except SQLAlchemyError as e:
            self.logger.error(f"{self._log_prefix} Failed to aggregate cluster usage: {e}")



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
                data = [
                    {'used': item.used, 'used_ratio': item.use_ratio,
                     'soft_limit': getattr(item, 'soft_limit', None),
                     'soft_use_ratio': getattr(item, 'soft_use_ratio', None),
                     f'{table_name}_id': str(item.id), 'updated_at': datetime.now()}
                    for item in items if item.used
                ]
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
                    item_dict = item.dict()
                    # item_dict['storage_cluster_id'] = self.storage_cluster_id
                    new_data.append(model(**item_dict))
                else:
                    for key, value in item.dict(exclude=set(exclude_keys)).items():
                        setattr(item_db, key, value)
                    self.db.merge(item_db)
            if new_data:
                self.db.add_all(new_data)

            if delete_redundant:
                data_keys = {tuple(getattr(item, key) for key in unique_keys) for item in data}
                extra_data = [item for key, item in existing_data_map.items() if key not in data_keys]
                if extra_data:
                    for item in extra_data:
                        self.db.delete(item)
                    self.logger.info(f"{self._log_prefix} Deleted {len(extra_data)} redundant {model.__name__} records")

            self.db.commit()
            self.logger.info(f"{self._log_prefix} Synced {len(data)} {model.__name__} records to PostgreSQL")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"{self._log_prefix} Failed to sync {model.__name__} to PostgreSQL: {e}")
            return False

    def _process_quota_user_isilon(self, record: Dict, qtree_map: Dict, group_map: Dict,
                                    users_map: Dict, users_uid_map: Dict,
                                    storage_usage_map: Dict) -> Optional[storageUsageSchema.StorageUsageBase]:
        """处理 isilon 用户配额记录"""
        try:
            vol_name = record.get('path')
            qtree_name = 'null'
            qtree_db = qtree_map.get((vol_name, qtree_name))
            if qtree_db is None:
                return None
            rd_username = record.get('rd_username', '').strip()
            limit = record.get('limit')
            soft_limit = record.get('soft_limit')
            used = record.get('used')
            use_ratio = record.get('use_ratio')
            soft_use_ratio = record.get('soft_use_ratio')
            qtree_id = qtree_db.id
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
                    self.db.commit()
                    user_id = new_user.id
                    users_map[rd_username] = user_id
            # qtree 可能对应多个 group
            group_dbs = group_map.get(qtree_id)
            if not group_dbs:
                return None
            elif len(group_dbs) == 1:
                group_db = group_dbs[0]
            else:
                group_db = group_dbs[0]

            if group_db and group_db.associate_multiple_groups is False:
                group_id = group_db.id
            else:
                su_db = storage_usage_map.get((user_id, qtree_id))
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

    def _process_quota_user_netapp(self, record: Dict, qtree_map: Dict, group_map: Dict,
                                    users_map: Dict, users_uid_map: Dict,
                                    storage_usage_map: Dict) -> Optional[storageUsageSchema.StorageUsageBase]:
        """处理 netapp 用户配额记录"""
        try:
            vol_name = record.get('volume', {}).get('name', '')
            qtree_name = record.get('qtree', {}).get('name', '') or 'null'
            qtree_db = qtree_map.get((vol_name, qtree_name))
            if qtree_db is None:
                return None

            users_list = record.get('users', [])
            if not users_list:
                return None
            user_entry = users_list[0]
            rd_username = user_entry.get('name', '').strip()
            uid_str = str(user_entry.get('id', ''))

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


            qtree_id = qtree_db.id
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
                    self.db.commit()
                    user_id = new_user.id
                    users_map[rd_username] = user_id

            group_dbs = group_map.get(qtree_id)
            if not group_dbs or len(group_dbs) > 1:
                group_db = None
            else:
                group_db = group_dbs[0]

            if group_db and group_db.associate_multiple_groups is False:
                group_id = group_db.id
            else:
                su_db = storage_usage_map.get((user_id, qtree_id))
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


    def _fetch_user_quotas_isilon(self,qtree_map, group_map,
                        users_map, users_uid_map, storage_usage_map) -> tuple[list[VolumeBase], list[StorageUsageBase]]:
        """Isilon 用户配额获取"""
        volumes =[]
        quotas = []
        if self.client is None:
            return volumes,quotas
        try:
            user_quotas = []
            group_quotas = []
            default_user_quotas_map = {}
            raw_quotas = self.client.get_quotas()


            for quota in raw_quotas:
                quota_type = quota.get('type')
                thresholds = quota.get('thresholds', {})
                path = quota.get('path')
                linked = quota.get('linked',False)
                usage = quota.get('usage', {})
                hard_bytes = thresholds.get('hard')
                soft_bytes = thresholds.get('soft')
                used_bytes = usage.get('logical')

                used = _bytes_to_gb(used_bytes)
                hard_limit = _bytes_to_gb(hard_bytes)
                soft_limit = _quota_limit_to_gb(soft_bytes)

                if quota_type == 'default-user':
                    default_user_quotas_map[path] = {
                        'hard_limit':hard_limit,
                        'soft_limit':soft_limit
                    }
                else:
                    quota_new = {
                        'path':path,
                        'linked':linked,
                        'used':used,
                        'hard_limit': hard_limit,
                        'soft_limit': soft_limit
                    }
                    if quota_type == 'user':
                        persona = quota.get('persona')
                        rd_username = persona.get('name', '').strip()
                        if rd_username in ('*', 'root', ''):
                            continue
                        quota_new['rd_username'] = rd_username
                        user_quotas.append(quota_new)
                    if quota_type == 'directory':
                        group_quotas.append(quota_new)

            for quota in user_quotas:
                path  = quota.get('path')
                linked = quota.get('linked')
                hard_limit = quota.get('hard_limit')
                soft_limit = quota.get('soft_limit')
                used = quota.get('used')
                if linked is True:
                    limit = default_user_quotas_map.get(path,{}).get('hard_limit')
                    soft_limit = default_user_quotas_map.get(path,{}).get('soft_limit')
                else:
                    limit = hard_limit
                use_ratio = _calculate_use_ratio(used, limit)
                soft_use_ratio = _calculate_use_ratio(used, soft_limit)
                quota['use_ratio'] = use_ratio
                quota['limit'] = limit
                quota['soft_limit'] = soft_limit
                quota['soft_use_ratio'] = soft_use_ratio
                item = self._process_quota_user_isilon(
                    quota, qtree_map, group_map,
                    users_map, users_uid_map, storage_usage_map
                )

                if item:
                    quotas.append(item)

            for group in group_quotas:
                path = group.get('path')
                hard_limit = group.get('hard_limit')
                soft_limit = group.get('soft_limit')
                used = group.get('used')
                limit = hard_limit
                use_ratio = _calculate_use_ratio(used, limit)
                soft_use_ratio = _calculate_use_ratio(used, soft_limit)

                volumes.append(volumeSchema.VolumeBase(
                    storage_cluster_id=self.storage_cluster_id,
                    name=path,
                    vserver='',
                    state='',
                    type='',
                    allocated=limit,
                    aggregate='isilon_cluster',
                    limit=limit,
                    soft_limit=soft_limit,
                    used=used,
                    use_ratio=use_ratio,
                    soft_use_ratio=soft_use_ratio,
                    updated_at=datetime.now()
                ))

            self.logger.info(f"{self._log_prefix} Fetched {len(quotas)} user quotas {len(volumes)} volumes")

            return volumes, quotas
        except Exception as e:
            self.logger.error(f"{self._log_prefix} Failed to fetch user quotas: {e}")
        return volumes, quotas
