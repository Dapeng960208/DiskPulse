# -*- coding: utf-8 -*-
from datetime import datetime
from crud.configCrud import get_storage_config
from sqlalchemy.exc import SQLAlchemyError
from utils.netAppClient import NetAppClient
from schemas import aggregateSchema, volumeSchema, qtreeSchema, storageUsageSchema
from models import Aggregate, Volume, Qtree, Group, StorageUsage, User, Project
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


class NetAppMonitor:
    """
    通过 NetApp ONTAP REST API 采集存储数据，并写入 MySQL 和 QuestDB。
    """

    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
        self.config = None
        self.client: Optional[NetAppClient] = None

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def start(self):
        self.setup()
        self.execute_data_collection()
        self.cleanup()

    def setup(self):
        self.config = get_storage_config(db=self.db)
        self.client = NetAppClient(
            hostname=self.config.storage_host,
            username=self.config.storage_user,
            password=self.config.storage_password,
            port=self.config.storage_port if self.config.storage_port else 443,
            logger=self.logger
        )
        self.logger.info(f"[Storage_Pulse] NetApp client initialized: {self.config.storage_host}:{self.config.storage_port or 443}")

    def cleanup(self):
        if self.client:
            self.client.close()
        self.db.commit()

    # ------------------------------------------------------------------
    # 数据采集主流程
    # ------------------------------------------------------------------

    def execute_data_collection(self):
        aggregates = self.fetch_aggregates()
        self.write_data_to_mysql(aggregates, Aggregate, ['name'])

        volumes = self.fetch_volumes()
        self.write_data_to_mysql(volumes, Volume, ['name'], delete_redundant=True)

        qtrees = self.fetch_qtrees()
        self.write_data_to_mysql(qtrees, Qtree, ['name', 'volume_id'], delete_redundant=True)
        self.update_volume_allocated()

        storage_usages = self.fetch_storage_usages()
        self.write_data_to_mysql(storage_usages, StorageUsage, ['group_id', 'user_id'],
                                 exclude_keys=['group_id', 'user_id'])
        self.update_group_storage_data()
        self.update_project_storage_data()
        self.write_data_to_quest_db('storage_usages', self.db.query(StorageUsage).filter(StorageUsage.used > 0).all())
        self.write_data_to_quest_db('qtree', self.db.query(Qtree).filter(Qtree.used >= 0).all())
        self.write_data_to_quest_db('volume', self.db.query(Volume).filter(Volume.used >= 0).all())
        self.write_data_to_quest_db('project', self.db.query(Project).filter(Project.used >= 0).all())
        self.write_data_to_quest_db('group', self.db.query(Group).filter(
            Group.enable_monitoring.is_(True), Group.qtree_id.isnot(None)).all())
        self.write_data_to_quest_db('aggregate', self.db.query(Aggregate).filter(Aggregate.used >= 0).all())

    # ------------------------------------------------------------------
    # 数据获取（通过 NetApp REST API）
    # ------------------------------------------------------------------

    def fetch_aggregates(self) -> List[aggregateSchema.AggregateBase]:
        result = []
        if self.client is None:
            return result
        try:
            records = self.client.get_aggregates()
            for rec in records:
                space = rec.get('space', {})
                total = _bytes_to_gb(space.get('block_storage', {}).get('size'))
                available = _bytes_to_gb(space.get('block_storage', {}).get('available'))
                if total is None or available is None:
                    continue
                used = round(total - available, 2)
                use_ratio = round(used * 100 / total, 2) if total else 0
                result.append(aggregateSchema.AggregateBase(
                    name=rec.get('name', ''),
                    limit=total,
                    used=used,
                    use_ratio=use_ratio,
                    updated_at=datetime.now()
                ))
        except Exception as e:
            self.logger.error(f"[Storage_Pulse] Failed to fetch NetApp aggregates: {e}")
        return result

    def fetch_volumes(self) -> List[volumeSchema.VolumeBase]:
        result = []
        if self.client is None:
            return result
        try:
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
        except Exception as e:
            self.logger.error(f"[Storage_Pulse] Failed to fetch NetApp volumes: {e}")
        return result

    def fetch_qtrees(self) -> List[qtreeSchema.QtreeBase]:
        result = []
        if self.client is None:
            return result
        try:
            existing_volumes = self.db.query(Volume).all()
            volumes_map = {vol.name: vol.id for vol in existing_volumes}
            records = self.client.get_qtrees()
            for rec in records:
                volume_name = rec.get('volume', {}).get('name', '')
                volume_id = volumes_map.get(volume_name)
                if volume_id is None:
                    continue
                name = rec.get('name', '')
                if name == '':
                    name = 'null'
                result.append(qtreeSchema.QtreeBase(
                    name=name,
                    volume_id=volume_id,
                    style=rec.get('security_style', ''),
                    oplocks=rec.get('oplocks', {}).get('enabled', False),
                    status=rec.get('statistics', {}).get('status', ''),
                    updated_at=datetime.now()
                ))
        except Exception as e:
            self.logger.error(f"[Storage_Pulse] Failed to fetch NetApp qtrees: {e}")
        return result

    def fetch_storage_usages(self) -> List[storageUsageSchema.StorageUsageBase]:
        result = []
        if self.client is None:
            return result
        try:
            # 构建辅助 map
            qtree_volume_dbs = self.db.query(Qtree, Volume.name).join(Qtree, Qtree.volume_id == Volume.id).all()
            qtree_map = {(volume_name, qtree.name): qtree for qtree, volume_name in qtree_volume_dbs}

            group_dbs = self.db.query(Group).filter(Group.enable_monitoring.is_(True)).all()
            group_map: Dict[int, List] = {}
            for g in group_dbs:
                group_map.setdefault(g.qtree_id, []).append(g)

            users = self.db.query(User).all()
            users_map = {u.rd_username: u.id for u in users if u}
            users_uid_map = {str(u.uid): u for u in users}

            su_dbs = self.db.query(StorageUsage).join(Group, StorageUsage.group_id == Group.id).filter(
                Group.associate_multiple_groups.is_(True)).all()
            storage_usage_map = {
                (su.user_id, su.group.qtree.id): su
                for su in su_dbs if su.group and su.group.qtree
            }

            records = self.client.get_quota_reports()
            for rec in records:
                quota_type = rec.get('type', '')
                if quota_type == 'user':
                    item = self._process_quota_user(
                        rec, qtree_map, group_map,
                        users_map, users_uid_map, storage_usage_map
                    )
                    if item:
                        result.append(item)
                elif quota_type == 'tree':
                    # 更新 qtree 使用量
                    vol_name = rec.get('volume', {}).get('name', '')
                    qtree_name = rec.get('qtree', {}).get('name', '') or 'null'
                    qtree_db = qtree_map.get((vol_name, qtree_name))
                    if qtree_db:
                        space = rec.get('space', {})
                        used = _bytes_to_gb(space.get('used'))
                        limit = _bytes_to_gb(space.get('hard_limit')) if space.get('hard_limit', -1) != -1 else None
                        use_ratio = round(used / limit * 100, 2) if limit and used is not None else None
                        qtree_db.limit = limit
                        qtree_db.used = used
                        qtree_db.use_ratio = use_ratio
                        self.db.commit()

        except Exception as e:
            self.logger.error(f"[Storage_Pulse] Failed to fetch NetApp storage usages: {e}")
        return result

    def _process_quota_user(self, record: Dict, qtree_map: Dict, group_map: Dict,
                            users_map: Dict, users_uid_map: Dict,
                            storage_usage_map: Dict) -> Optional[storageUsageSchema.StorageUsageBase]:
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
            files_rec = record.get('files', {})
            used = _bytes_to_gb(space.get('used'))
            hard_limit = space.get('hard_limit', -1)
            limit = _bytes_to_gb(hard_limit) if hard_limit not in (None, -1) else None
            use_ratio = round(used / limit * 100, 2) if limit and used is not None else None
            file_used = files_rec.get('used', 0) or 0
            file_hard = files_rec.get('hard_limit', -1)
            file_limit = file_hard if file_hard not in (None, -1) else None

            qtree_id = qtree_db.id

            if uid_str.isdigit():
                user = users_uid_map.get(uid_str)
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
                    user_id=user_id, group_id=group_id, limit=limit, used=used,
                    use_ratio=use_ratio, file_used=file_used, linux_path=linux_path,
                    file_limit=file_limit, updated_at=datetime.now()
                )
        except Exception as e:
            self.logger.error(f"Failed to process quota user record: {e}")
        return None

    # ------------------------------------------------------------------
    # 写库逻辑（与 StoreMonitor 保持一致）
    # ------------------------------------------------------------------

    def update_volume_allocated(self):
        """更新 volume 已分配给 Qtree 的容量"""
        volume_dbs = self.db.query(Volume).all()
        for volume_db in volume_dbs:
            qtree_sum = self.db.query(func.sum(Qtree.limit)).filter(
                Qtree.volume_id == volume_db.id,
                Qtree.name != 'null',
                Qtree.used > 0
            ).scalar()
            volume_db.allocated = qtree_sum if qtree_sum else volume_db.limit
            self.db.commit()

    def write_data_to_mysql(self, data: List, model, unique_keys: List[str],
                            exclude_keys: List[str] = [], delete_redundant: bool = False):
        if not data:
            return False
        try:
            existing_data = self.db.query(model).all()
            existing_data_map = {
                tuple(getattr(item, key) for key in unique_keys): item
                for item in existing_data
            }
            new_data = []
            for item in data:
                item_key = tuple(getattr(item, key) for key in unique_keys)
                item_db = existing_data_map.get(item_key)
                if item_db is None:
                    new_data.append(model(**item.dict()))
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
                    self.logger.info(f"[Storage_Pulse] {model.__name__}: deleted {len(extra_data)} redundant records")

            self.db.commit()
            self.logger.info(f"[Storage_Pulse] {model.__name__}: synced {len(data)} records to PostgreSQL")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"[Storage_Pulse] Failed to write {model.__name__} data to PostgreSQL: {e}")
            return False

    def write_data_to_quest_db(self, table_name: str, items: List):
        if not items:
            return
        try:
            if table_name != 'storage_usages':
                data = [
                    {'used': item.used, 'used_ratio': item.use_ratio,
                     f'{table_name}_id': str(item.id), 'updated_at': datetime.now()}
                    for item in items if item.used
                ]
                table_name = f"{table_name}_storage_usages"
            else:
                data = [
                    {'used': item.used, 'used_ratio': item.use_ratio, 'file_used': item.file_used,
                     f'{table_name[:-1]}_id': str(item.id), 'updated_at': item.updated_at,
                     'user_id': str(item.user_id)}
                    for item in items if item.used
                ]
            if not data:
                return
            with QuestDBSession(self.config) as conn:
                trans = conn.begin()
                keys = ', '.join(data[0].keys())
                placeholders = ', '.join([f":{k}" for k in data[0].keys()])
                insert_command = text(
                    f"INSERT BATCH {len(data)} INTO {table_name} ({keys}) VALUES ({placeholders});"
                )
                conn.execute(insert_command, data)
                trans.commit()
            self.logger.info(f"[Storage_Pulse] QuestDB [{table_name}]: inserted {len(data)} records")
        except Exception as e:
            self.logger.error(f"[Storage_Pulse] Failed to write to QuestDB [{table_name}]: {e}")

    def update_group_storage_data(self):
        # case0: qtree_id 为空
        case0_dbs = self.db.query(Group).filter(
            Group.enable_monitoring.is_(True), Group.qtree_id.is_(None)).all()
        for group_db in case0_dbs:
            group_db.limit = 0
            group_db.used = 0
            group_db.use_ratio = 0
            self.db.commit()

        # case1: 与 volume 直接关联（qtree name == 'null'）
        case1_dbs = self.db.query(Group, Qtree, Volume)\
            .join(Group, Qtree.id == Group.qtree_id)\
            .join(Volume, Qtree.volume_id == Volume.id)\
            .filter(
                Qtree.name == 'null',
                Group.associate_multiple_groups.is_(False),
                Group.enable_monitoring.is_(True),
                Group.qtree_id.isnot(None)
            ).all()
        for group_db, qtree_db, volume_db in case1_dbs:
            group_db.limit = volume_db.limit
            group_db.used = volume_db.used
            group_db.use_ratio = volume_db.use_ratio
            self.db.commit()

        # case2: 与 qtree 直接关联
        case2_dbs = self.db.query(Group, Qtree)\
            .join(Group, Qtree.id == Group.qtree_id)\
            .filter(
                Qtree.name != 'null',
                Group.associate_multiple_groups.is_(False),
                Group.enable_monitoring.is_(True),
                Group.qtree_id.isnot(None)
            ).all()
        for group_db, qtree_db in case2_dbs:
            group_db.limit = qtree_db.limit
            group_db.used = qtree_db.used
            group_db.use_ratio = qtree_db.use_ratio
            self.db.commit()

        # case3: 分组聚合计算
        case3_dbs = self.db.query(
            Group.id, func.sum(StorageUsage.used), func.sum(StorageUsage.limit)
        ).join(Group, StorageUsage.group_id == Group.id)\
            .filter(
                Group.associate_multiple_groups.is_(True),
                Group.enable_monitoring.is_(True),
                Group.qtree_id.isnot(None)
            ).group_by(Group.id).all()
        for group_id, sum_used, sum_limit in case3_dbs:
            group_db = self.db.query(Group).filter_by(id=group_id).first()
            sum_used = sum_used if sum_used else 0
            sum_limit = sum_limit if sum_limit else 0
            group_db.used = sum_used
            limit = group_db.limit if group_db.limit is not None else sum_limit
            use_ratio = round((sum_used * 100) / limit, 2) if limit > 0 else 0
            group_db.limit = limit
            group_db.use_ratio = use_ratio
            group_db.updated_at = datetime.now()
            self.db.commit()

        self.logger.info("[Storage_Pulse] Group storage data updated")

    def update_project_storage_data(self):
        try:
            project_store_dbs = self.db.query(
                Group.project_id, func.sum(Group.used), func.sum(Group.limit)
            ).filter(
                Group.enable_monitoring.is_(True),
                Group.qtree_id.isnot(None)
            ).group_by(Group.project_id).all()

            for project_id, used, limit in project_store_dbs:
                use_ratio = round((used * 100 / limit), 2) if limit else None
                self.db.query(Project).filter_by(id=project_id).update(
                    {'limit': limit, 'used': used, 'use_ratio': use_ratio,
                     'updated_at': datetime.now()}
                )
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.logger.error(f"[Storage_Pulse] Failed to update project storage data: {e}")
            return False
