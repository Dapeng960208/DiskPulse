# -*- coding: utf-8 -*-
from datetime import datetime
from crud.configCrud import get_storage_config
from sqlalchemy.exc import SQLAlchemyError
from utils.isilonClient import IsilonClient
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


class IsilonMonitor:
    """
    通过 Isilon OneFS REST API 采集存储数据，并写入 PostgreSQL 和 QuestDB。
    """

    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
        self.config = None
        self.client: Optional[IsilonClient] = None

    def start(self):
        self.setup()
        self.execute_data_collection()
        self.cleanup()

    def setup(self):
        self.config = get_storage_config(db=self.db)
        self.client = IsilonClient(
            hostname=self.config.storage_host,
            username=self.config.storage_user,
            password=self.config.storage_password,
            port=self.config.storage_port if self.config.storage_port else 8080,
            logger=self.logger
        )
        self.logger.info(f"[Storage_Pulse] Isilon client initialized: {self.config.storage_host}:{self.config.storage_port or 8080}")

    def cleanup(self):
        if self.client:
            self.client.close()
        self.db.commit()

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

    def fetch_aggregates(self) -> List[aggregateSchema.AggregateBase]:
        result = []
        if self.client is None:
            return result
        try:
            stats = self.client.get_cluster_stats()
            if stats:
                total = _bytes_to_gb(stats.get('total'))
                available = _bytes_to_gb(stats.get('avail'))
                if total is not None and available is not None:
                    used = round(total - available, 2)
                    use_ratio = round(used * 100 / total, 2) if total else 0
                    result.append(aggregateSchema.AggregateBase(
                        name='isilon_cluster',
                        limit=total,
                        used=used,
                        use_ratio=use_ratio,
                        updated_at=datetime.now()
                    ))
        except Exception as e:
            self.logger.error(f"[Storage_Pulse] Failed to fetch Isilon aggregates: {e}")
        return result

    def fetch_volumes(self) -> List[volumeSchema.VolumeBase]:
        result = []
        if self.client is None:
            return result
        try:
            exports = self.client.get_exports()
            for exp in exports:
                paths = exp.get('paths', [])
                if not paths:
                    continue
                path = paths[0]
                result.append(volumeSchema.VolumeBase(
                    name=path,
                    vserver='',
                    state='online',
                    type='rw',
                    aggregate='isilon_cluster',
                    limit=0,
                    used=0,
                    use_ratio=0,
                    updated_at=datetime.now()
                ))
        except Exception as e:
            self.logger.error(f"[Storage_Pulse] Failed to fetch Isilon volumes: {e}")
        return result

    def fetch_qtrees(self) -> List[qtreeSchema.QtreeBase]:
        return []

    def fetch_storage_usages(self) -> List[storageUsageSchema.StorageUsageBase]:
        result = []
        if self.client is None:
            return result
        try:
            group_dbs = self.db.query(Group).filter(Group.enable_monitoring.is_(True)).all()
            group_map = {g.linux_path: g for g in group_dbs if g.linux_path}

            users = self.db.query(User).all()
            users_map = {u.rd_username: u.id for u in users if u}

            quotas = self.client.get_quotas()
            for quota in quotas:
                if quota.get('type') != 'user':
                    continue
                
                persona = quota.get('persona')
                if not persona or persona.get('type') != 'user':
                    continue
                
                rd_username = persona.get('name', '').strip()
                if rd_username in ('*', 'root', ''):
                    continue

                thresholds = quota.get('thresholds', {})
                usage = quota.get('usage', {})
                used = _bytes_to_gb(usage.get('logical'))
                hard_limit = thresholds.get('hard')
                limit = _bytes_to_gb(hard_limit) if hard_limit not in (None, 0) else None
                use_ratio = round(used / limit * 100, 2) if limit and used is not None else None

                path = quota.get('path', '')
                group_db = None
                for gpath, g in group_map.items():
                    if path.startswith(gpath):
                        group_db = g
                        break
                
                if not group_db:
                    continue

                user_id = users_map.get(rd_username)
                if not user_id:
                    new_user = User(rd_username=rd_username, updated_at=datetime.now())
                    self.db.add(new_user)
                    self.db.commit()
                    user_id = new_user.id
                    users_map[rd_username] = user_id

                linux_path = f"{group_db.linux_path}/{rd_username}".replace('//', '/')
                result.append(storageUsageSchema.StorageUsageBase(
                    user_id=user_id, group_id=group_db.id, limit=limit, used=used,
                    use_ratio=use_ratio, file_used=0, linux_path=linux_path,
                    file_limit=None, updated_at=datetime.now()
                ))
        except Exception as e:
            self.logger.error(f"[Storage_Pulse] Failed to fetch Isilon storage usages: {e}")
        return result

    def update_volume_allocated(self):
        """Isilon 无 qtree，跳过此步骤"""
        pass

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
                    self.logger.info(f"{model.__name__}: deleted {len(extra_data)} redundant records")

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
        group_dbs = self.db.query(Group).filter(Group.enable_monitoring.is_(True)).all()
        for group_db in group_dbs:
            sum_result = self.db.query(
                func.sum(StorageUsage.used), func.sum(StorageUsage.limit)
            ).filter(StorageUsage.group_id == group_db.id).first()
            
            sum_used = sum_result[0] if sum_result[0] else 0
            sum_limit = sum_result[1] if sum_result[1] else 0
            
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
                Group.enable_monitoring.is_(True)
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
