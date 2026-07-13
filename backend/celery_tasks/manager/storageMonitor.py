# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
import shlex

from schemas.storageUsageSchema import StorageUsageBase
from utils.common import format_to_gb
from crud.configCrud import get_storage_config
import re
from sqlalchemy.exc import SQLAlchemyError
from utils.sshClient import SSHClientBase
from schemas import aggregateSchema, volumeSchema, qtreeSchema, storageUsageSchema, groupSchema
from models import Aggregate, Volume, Qtree, Group, StorageUsage, User, Project, Host, StorageAlerts
from sqlalchemy import func, text
from dependencies import QuestDBSession
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from utils.mailTools.emailNotification import EmailNotification
from typing import Any, Dict, Optional, Tuple, List
from utils.storageTarget import resolve_group_storage_target


class DataParser(ABC):
    def __init__(self, db, logger, ssh):
        self.db = db
        self.logger = logger
        self.ssh = ssh

    @abstractmethod
    def parse(self):
        raise NotImplementedError("Parse method must be implemented by subclass.")


class AggregateDataParser(DataParser):
    def parse(self) -> List[aggregateSchema.AggregateBase]:
        result = []
        if self.ssh is None:
            return result
        flag, output = self.ssh.execute_command(command='aggr show')
        if not flag:
            return result
        for line in output:
            match_obj = re.match(r'(\S+)\s+(.+?B)\s+(.+?B)\s+(\d+%)', line)
            if match_obj:
                name = match_obj.group(1).strip()
                limit = format_to_gb(match_obj.group(2).strip()[:-1])
                store_available = format_to_gb(match_obj.group(3).strip()[:-1])
                used = round(limit - store_available, 2)
                use_ratio = round((used * 100 / limit), 2)
                aggregate = aggregateSchema.AggregateBase(
                    name=name, limit=limit, used=used,
                    use_ratio=use_ratio, updated_at=datetime.now()
                )
                result.append(aggregate)
        return result


class VolumeDataParser(DataParser):
    def parse(self) -> List[volumeSchema.VolumeBase]:
        result = []
        if self.ssh is None:
            return result
        flag, output = self.ssh.execute_command(command='vol show')
        if not flag:
            return result
        for line in output:
            match_obj = re.match(r'(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+?B)\s+(.+?B)\s+(\d+%)', line)
            if match_obj:
                vserver = match_obj.group(1)
                volume_name = match_obj.group(2)
                aggregate = match_obj.group(3)
                state = match_obj.group(4)
                type = match_obj.group(5)
                limit = format_to_gb(match_obj.group(6).strip()[:-1])
                store_available = format_to_gb(match_obj.group(7).strip()[:-1])
                used = round(limit - store_available, 2)
                use_ratio = round((used * 100 / limit), 2)
                volume = volumeSchema.VolumeBase(
                    name=volume_name, vserver=vserver, state=state, type=type,
                    aggregate=aggregate, limit=limit, used=used,
                    use_ratio=use_ratio, updated_at=datetime.now()
                )
                result.append(volume)
        self.logger.info(f"Successfully parsed volumes data, length: {len(result)}")
        return result


class QtreeDataParser(DataParser):
    def parse(self) -> List[qtreeSchema.QtreeBase]:
        result = []
        if self.ssh is None:
            return result
        flag, output = self.ssh.execute_command(command='qtree show')
        if not flag:
            return result
        existing_volumes = self.db.query(Volume).all()
        existing_volumes_map = {vol.name: vol.id for vol in existing_volumes}
        for line in output:
            match_obj = re.match(r'(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', line.strip())
            if match_obj:
                qtree_name = match_obj.group(3) if match_obj.group(3) != '""' else 'null'
                volume_name = match_obj.group(2).strip()
                volume_id = existing_volumes_map.get(volume_name)
                if volume_id is None:
                    continue
                style = match_obj.group(4)
                oplocks = match_obj.group(5)
                status = match_obj.group(6)
                qtree = qtreeSchema.QtreeBase(
                    name=qtree_name, volume_id=volume_id, style=style, oplocks=oplocks,
                    status=status, updated_at=datetime.now()
                )
                result.append(qtree)
        # quota_flag, quota_output = self.ssh.execute_command('quota report -quota-type tree')
        self.logger.info(f"Successfully parsed Qtree data, length: {len(result)}")
        return result


class StorageUsageDataParser(DataParser):
    def __init__(self, db, logger, ssh):
        super().__init__(db, logger, ssh)
        self.storage_usage_map = None
        self.users_uid_map = None
        self.users_map = None

    def parse(self) -> list[StorageUsageBase] | None:
        try:
            qtree_map = self.get_qtree_map()
            group_map = self.get_group_map()
            self.get_user_maps()
            self.get_storage_usages_maps()
            command = 'quota report'
            flag, output = self.ssh.execute_command(command=command)
            return self.process_quota_report(output, qtree_map, group_map)
        except Exception as e:
            self.logger.error(f"Error in StorageUsageDataParser:{e} ")
            return None

    def get_qtree_map(self) -> dict:
        try:
            qtree_volume_dbs = self.db.query(Qtree, Volume.name).join(Qtree, Qtree.volume_id == Volume.id).all()
            return {(volume_name, qtree.name): qtree for qtree, volume_name in qtree_volume_dbs}
        except Exception as e:
            self.logger.error(f"Error in get qtree map:{e}")
            return {}

    def get_group_map(self) -> dict:
        group_dbs = self.db.query(Group).filter(Group.enable_monitoring.is_(True)).all()
        result = {}
        for group in group_dbs:
            if group.qtree_id not in result:
                result[group.qtree_id] = [group]
            else:
                result[group.qtree_id].append(group)
        return result

    def get_user_maps(self):
        users = self.db.query(User).all()
        self.users_map = {user.rd_username: user.id for user in users if user}
        self.users_uid_map = {str(user.uid): user for user in users}

    def get_storage_usages_maps(self):
        storage_usages = self.db.query(StorageUsage).join(Group, StorageUsage.group_id == Group.id).filter(
            Group.associate_multiple_groups.is_(True)).all()
        self.storage_usage_map = {(storage_usage.user_id, storage_usage.group.qtree.id): storage_usage for storage_usage
                                  in storage_usages if storage_usage.group and storage_usage.group.qtree}

    def process_quota_report(self, output: List[str], qtree_map: dict, group_map: dict) \
            -> List[storageUsageSchema.StorageUsageBase]:
        result = []
        if output is None:
            self.logger.warning("No quota report output provided.")
            return result
        for line in output:
            match_obj = re.match(
                r'(\S+)\s(.+?)\s(user|tree)\s+(\S+)\s+(\S+B)\s+(\S+B|-)\s+(\d+)\s+(\d+|-)(.+)?',
                line.strip()
            )
            if match_obj:
                data = self.parse_storage_data_line(match_obj, qtree_map, group_map)
                if data:
                    result.append(data)
            # else:
            #     self.logger.warning(line)
        return result

    def parse_storage_data_line(self, match_obj, qtree_map, group_map) -> storageUsageSchema.StorageUsageBase | None:
        try:
            volume_name, qtree_name, type, rd_username, raw_used, raw_limit, file_used_str, file_limit_str, *rest = match_obj.groups()
            # if volume_name == 'ic_prj_DFB':
            #     self.logger.warning(f"volume_name:{volume_name}, qtree_name:{qtree_name}, type:{type}, rd_username:{rd_username}, raw_used:{raw_used}")
            used = format_to_gb(raw_used[:-1])
            limit = format_to_gb(raw_limit[:-1]) if raw_limit != '-' else None
            use_ratio = round((used / limit * 100), 2) if limit else None
            file_used = int(file_used_str)
            file_limit = int(file_limit_str) if file_limit_str != '-' else None
            qtree_name = qtree_name.strip()
            if len(qtree_name) == 0:
                qtree_name = 'null'
            qtree_db = qtree_map.get((volume_name, qtree_name))
            if qtree_db is None:
                return None
            if type == 'user':
                return self.process_user_storage(qtree_db, group_map, str(rd_username.strip()), limit, used,
                                                 use_ratio, file_used, file_limit)
            elif type == 'tree':
                self.update_qtree_usage(qtree_db, limit, used, use_ratio)
        except Exception as e:
            self.logger.error(f"Error in parsing storage data line:{e}")

    def update_qtree_usage(self, qtree_db, limit, used, use_ratio):
        qtree_db.limit = limit
        qtree_db.used = used
        qtree_db.use_ratio = use_ratio
        self.db.commit()

    def process_user_storage(self, qtree_db, group_map, rd_username, limit, used, use_ratio, file_used,
                             file_limit) -> storageUsageSchema.StorageUsageBase | None:
        global storage_usage_db
        try:
            if rd_username in ["*", "root"]:
                return
            qtree_id = qtree_db.id
            group_dbs = group_map.get(qtree_id)

            if rd_username.isdigit():
                user = self.users_uid_map.get(rd_username)
                if not user:
                    # self.logger.warning(f"{rd_username} no uid")
                    return
                user_id = user.id
                rd_username = user.rd_username
            else:
                user_id = self.users_map.get(rd_username)
                if not user_id:
                    user = User(rd_username=rd_username, updated_at=datetime.now())
                    self.db.add(user)
                    self.db.commit()
                    user_id = user.id
                    self.users_map[rd_username] = user
            if not group_dbs or len(group_dbs) > 1:
                group_db = None
            else:
                group_db = group_dbs[0]
            if group_db and group_db.associate_multiple_groups is False:
                group_id = group_db.id
            else:
                if self.storage_usage_map is None:
                    return
                storage_usage_db = self.storage_usage_map.get((user_id, qtree_id))
                if storage_usage_db is None:
                    # self.logger.warning(f"Can not get user storage {user_id} {qtree_db.name }{qtree_db.id}")
                    return
                group_db = storage_usage_db.group
                group_id = storage_usage_db.group_id
            if user_id and group_id:
                linux_path = f"{group_db.linux_path}/{rd_username}".replace("//", '/')
                return storageUsageSchema.StorageUsageBase(
                    user_id=user_id, group_id=group_id, limit=limit, used=used,
                    use_ratio=use_ratio, file_used=file_used, linux_path=linux_path,
                    file_limit=file_limit, updated_at=datetime.now()
                )
            return None
        except Exception as e:
            self.logger.error(f'Error in process_user_storage:{e}')


# StoreMonitor 类
class StoreMonitor:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
        self.config = None
        self.ssh = None

    def start(self):
        self.setup()
        self.execute_data_collection()
        self.cleanup()

    def create_ssh(self):
        hostname = self.config.storage_host
        port = self.config.storage_port if self.config.storage_port else 22
        username = self.config.storage_user
        password = self.config.storage_password
        return SSHClientBase(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            logger=self.logger
        )

    def setup(self):
        self.config = get_storage_config(db=self.db)
        self.ssh = self.create_ssh()

    def execute_data_collection(self):
        # 解析和写入数据
        aggregates = self.parse_data(AggregateDataParser(db=self.db, logger=self.logger, ssh=self.ssh))
        self.write_data_to_mysql(aggregates, Aggregate, ['name'])

        volumes = self.parse_data(VolumeDataParser(db=self.db, logger=self.logger, ssh=self.ssh))
        self.write_data_to_mysql(volumes, Volume, ['name'], delete_redundant=True)

        qtrees = self.parse_data(QtreeDataParser(db=self.db, logger=self.logger, ssh=self.ssh))
        self.write_data_to_mysql(qtrees, Qtree, ['name', 'volume_id'],
                                 delete_redundant=True)
        self.update_volume_allocated()

        storage_usages = self.parse_data(StorageUsageDataParser(db=self.db, logger=self.logger, ssh=self.ssh))
        self.write_data_to_mysql(storage_usages, StorageUsage, ['group_id', 'user_id'],
                                 exclude_keys=['group_id', 'user_id'])
        self.update_group_storage_data()
        self.update_project_storage_data()
        self.write_data_to_quest_db('storage_usages', self.db.query(StorageUsage).filter(StorageUsage.used > 0).all())
        self.write_data_to_quest_db('qtree', self.db.query(Qtree).filter(Qtree.used >= 0).all())
        self.write_data_to_quest_db('volume', self.db.query(Volume).filter(Volume.used >= 0).all())
        self.write_data_to_quest_db('project', self.db.query(Project).filter(Project.used >= 0).all())
        self.write_data_to_quest_db('group', self.db.query(Group).filter(Group.enable_monitoring.is_(True),
                                                                         Group.qtree_id.isnot(None)).all())
        self.write_data_to_quest_db('aggregate', self.db.query(Aggregate).filter(Aggregate.used >= 0).all())

    def cleanup(self):
        # 关闭连接和清理资源
        self.ssh.close_ssh_connection()
        self.db.commit()

    def update_volume_allocated(self):
        """更新volume已分配给Qtree的容量"""
        volume_dbs = self.db.query(Volume).all()
        for volume_db in volume_dbs:
            qtree_sum = self.db.query(func.sum(Qtree.limit)).filter(Qtree.volume_id == volume_db.id,
                                                                    Qtree.name != 'null',
                                                                    Qtree.used > 0).scalar()
            if qtree_sum:
                volume_db.allocated = qtree_sum
            else:
                volume_db.allocated = volume_db.limit
            self.db.commit()
        self.logger.info("Update Volume allocated size")

    def parse_data(self, parser: DataParser):
        try:
            return parser.parse()
        except Exception as e:
            self.logger.error(f"error in data parser:{e}")

    def write_data_to_mysql(self, data: List, model, unique_keys: List[str], exclude_keys: List[str] = [],
                            delete_redundant: bool = False):
        if not data:
            self.logger.warning(f"No {model.__name__} data to write to MySQL.")
            return False
        try:
            existing_data = self.db.query(model).all()
            existing_data_map = {tuple(getattr(item, key) for key in unique_keys): item for item in existing_data}
            new_data = []
            for item in data:
                item_key = tuple(getattr(item, key) for key in unique_keys)
                item_db = existing_data_map.get(item_key)

                if item_db is None:
                    new_data.append(model(**item.model_dump()))
                else:
                    for key, value in item.model_dump(exclude=exclude_keys).items():
                        setattr(item_db, key, value)
                    self.db.merge(item_db)
            if new_data:
                self.db.add_all(new_data)

            if delete_redundant is True:
                data_keys = {tuple(getattr(item, key) for key in unique_keys) for item in data}

                # Identify extra existing data to delete
                extra_data = [item for key, item in existing_data_map.items() if key not in data_keys]
                if extra_data:
                    for item in extra_data:
                        self.db.delete(item)
                    self.logger.info(f"{model.__name__} delete redundant data from MySQL :{len(extra_data)} ")

            self.db.commit()
            self.logger.info(f"{model.__name__} data successfully written to MySQL, length:{len(data)}")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Error writing {model.__name__} data to MySQL: {e}")
            return False

    def write_data_to_quest_db(self, table_name: str, items: List):
        if len(items) == 0:
            self.logger.warning(f"No Data need to write in {table_name} ")
            return
        # 实现写入 QuestDB 数据的逻辑
        try:
            if table_name != 'storage_usages':
                data = [{'used': item.used, 'used_ratio': item.use_ratio,
                         f'{table_name}_id': str(item.id), 'updated_at': datetime.now()} for
                        item in items if item.used]
                table_name = f"{table_name}_storage_usages"
            else:
                data = [{'used': item.used, 'used_ratio': item.use_ratio, 'file_used': item.file_used,
                         f'{table_name[:-1]}_id': str(item.id), 'updated_at': item.updated_at,
                         'user_id': str(item.user_id)}
                        for item in items if item.used]

            with QuestDBSession(self.config) as conn:
                trans = conn.begin()
                keys = ', '.join(data[0].keys())
                placeholders = ', '.join([f":{key}" for key in data[0].keys()])
                insert_command = text(f"INSERT  BATCH {len(data)} INTO {table_name} ({keys}) VALUES ({placeholders});")
                conn.execute(insert_command, data)
                trans.commit()
            self.logger.info(f"{table_name.capitalize()} data successfully written to QuestDB,length:{len(data)}")
        except Exception as e:
            self.logger.error(f"Error writing {table_name} data to QuestDB: {e}")

    def update_group_storage_data(self):
        # qtree id 为空
        case0_dbs = self.db.query(Group).filter(Group.enable_monitoring.is_(True), Group.qtree_id.is_(None)).all()
        for group_db in case0_dbs:
            group_db.limit = 0
            group_db.used = 0
            group_db.use_ratio = 0
            self.db.commit()
        # 和volume直接关联
        case1_dbs = self.db.query(Group, Qtree, Volume).join(Group, Qtree.id == Group.qtree_id).join(Volume,
                                                                                                     Qtree.volume_id == Volume.id).filter(
            Qtree.name == 'null', Group.associate_multiple_groups.is_(False), Group.enable_monitoring.is_(True),
            Group.qtree_id.isnot(None)).all()
        for group_db, qtree_db, volume_db in case1_dbs:
            group_db.limit = volume_db.limit
            group_db.used = volume_db.used
            group_db.use_ratio = volume_db.use_ratio
            self.db.commit()
        # 和qtree直接关联
        case2_dbs = self.db.query(Group, Qtree).join(Group, Qtree.id == Group.qtree_id).filter(Qtree.name != 'null',
                                                                                               Group.associate_multiple_groups.is_(
                                                                                                   False),
                                                                                               Group.enable_monitoring.is_(
                                                                                                   True),
                                                                                               Group.qtree_id.isnot(
                                                                                                   None)).all()
        for group_db, qtree_db in case2_dbs:
            group_db.limit = qtree_db.limit
            group_db.used = qtree_db.used
            group_db.use_ratio = qtree_db.use_ratio
            self.db.commit()
        # 无法关联，分组计算

        case3_dbs = self.db.query(Group.id, func.sum(StorageUsage.used), func.sum(StorageUsage.limit)).join(Group,
                                                                                                            StorageUsage.group_id == Group.id).filter(
            Group.associate_multiple_groups.is_(True), Group.enable_monitoring.is_(True),
            Group.qtree_id.isnot(None)).group_by(Group.id).all()
        for (group_id, sum_used, sum_limit) in case3_dbs:
            group_db = self.db.query(Group).filter_by(id=group_id).first()
            sum_used = sum_used if sum_used else 0
            sum_limit = sum_limit if sum_limit else 0
            group_db.used = sum_used
            if group_db.limit is None:
                limit = sum_limit
            else:
                limit = group_db.limit
            use_ratio = round((sum_used * 100) / limit, 2) if limit > 0 else 0
            group_db.limit = limit
            group_db.use_ratio = use_ratio
            group_db.updated_at = datetime.now()
            self.db.commit()
            # self.logger.info(f'Update {group_db.name} {sum_used} {sum_limit}')
        self.logger.info('Update Group StorageUsage successfully')

    def update_project_storage_data(self):
        # 实现更新项目存储数据的逻辑
        try:
            project_store_dbs = self.db.query(
                Group.project_id, func.sum(Group.used), func.sum(Group.limit)
            ).filter(Group.enable_monitoring.is_(True), Group.qtree_id.isnot(None)).group_by(Group.project_id).all()
            for project_id, used, limit in project_store_dbs:
                use_ratio = round((used * 100 / limit), 2) if limit else None
                self.db.query(Project).filter_by(id=project_id).update(
                    {'limit': limit, 'used': used, 'use_ratio': use_ratio,
                     'updated_at': datetime.now()}
                )
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.logger.error(f"Error updating project store data: {e}")
            return False


class FileInfo(BaseModel):
    file: str = Field(..., alias='File')
    size: int = Field(..., alias='Size')
    blocks: int = Field(..., alias='Blocks')
    io_block: int = Field(..., alias='IO Block')
    type: str = Field(..., alias='Type')
    device: str = Field(..., alias='Device')
    inode: str = Field(..., alias='Inode')
    links: int = Field(..., alias='Links')
    access: str = Field(..., alias='Access')
    gid: str = Field(..., alias='Gid')
    access_time: str = Field(..., alias='Access Time')
    modify_time: str = Field(..., alias='Modify Time')
    change_time: str = Field(..., alias='Change Time')
    birth_time: str | None = Field(None, alias='Birth Time')


class UserUid(BaseModel):
    rd_username: str = Field(..., alias='rdUsername')
    uid: int = Field(..., alias='Uid')


class SynchronousPathState:
    def __init__(self, db, logger):
        self.users_uid_map = None
        self.users_map = None
        self.db = db
        self.logger = logger
        self.config = None
        self.ssh = None

    def start(self):
        self.setup()
        self.synchronous_path_state()
        self.collect_statistics_on_user_storage_usage()
        self.clean_up()

    def create_ssh(self):
        hostname = self.config.storage_host
        port = self.config.storage_port if self.config.storage_port else 22
        username = self.config.storage_user
        password = self.config.storage_password
        return SSHClientBase(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            logger=self.logger
        )

    def setup(self):
        self.config = get_storage_config(db=self.db)

    def clean_up(self):
        self.db.commit()

    def synchronous_path_state(self):
        user_dbs = self.db.query(User).all()
        self.users_map = {user.rd_username: user for user in user_dbs}
        self.users_uid_map = {user.uid: user for user in user_dbs}
        group_dbs = self.db.query(Group).filter(Group.enable_monitoring.is_(True)).all()
        for group_db in group_dbs:
            host = self.db.query(Host).filter_by(id=group_db.monitor_host_id).first()
            if host is None or host.ip is None or len(host.ip.strip()) == 0:
                self.logger.error('No host info')
                continue

            host_ip = host.ip
            self.logger.info(f'Login in {host_ip}, group {group_db.linux_path}')
            ssh_client = SSHClientBase(hostname=host_ip, port=22, password=self.config.storage_password,
                                       username=self.config.storage_user, logger=self.logger)
            flag, lines = ssh_client.execute_command(command=f"ls {group_db.linux_path}")
            if not flag:
                continue

            lines = [line.strip('\n').replace('.', '') for line in lines]
            rd_usernames = [line for line in lines if len(line) > 0]
            storage_usage_dbs = self.db.query(StorageUsage).filter_by(group_id=group_db.id).all()
            exit_storage_usage_map = {storage_usage_db.user_id: storage_usage_db for storage_usage_db in
                                      storage_usage_dbs}
            exit_user_ids = set(exit_storage_usage_map.keys())
            for item in rd_usernames:
                user_path = f"{group_db.linux_path}/{item}".replace('//', '/')
                flag, output = ssh_client.execute_command(f'stat {user_path}',check_output=False)
                if flag is False:
                    continue
                path_info, user_uid_info = self.parse(output)
                uid = user_uid_info.uid
                rd_username = user_uid_info.rd_username if user_uid_info.rd_username != 'UNKNOWN' else item

                if uid == '0' or rd_username == 'root':
                    continue
                user_db = self.users_map.get(rd_username)
                if user_db is None:
                    user_db = self.users_uid_map.get(uid)
                    if user_db is None:
                        try:
                            user_db = User(rd_username=rd_username, uid=user_uid_info.uid, is_quit=True)
                            self.db.add(user_db)
                            self.db.commit()
                            self.users_map[user_uid_info.rd_username] = user_db
                            self.users_uid_map[uid] = user_db
                        except Exception as e:
                            self.logger.error(e)
                            continue
                else:
                    if user_db.uid is None:
                        user_db.uid = user_uid_info.uid
                        user_db.updated_at = datetime.now()
                storage_usage_db = exit_storage_usage_map.get(user_db.id)
                if not storage_usage_db:
                    storage_usage_db = StorageUsage(user_id=user_db.id, group_id=group_db.id, linux_path=user_path)
                    self.db.add(storage_usage_db)
                    self.db.commit()
                    exit_storage_usage_map[user_db.id] = storage_usage_db
                else:
                    exit_user_ids.discard(user_db.id)
                for key, value in path_info.model_dump(exclude={'file'}).items():
                    setattr(storage_usage_db, key, value)
                storage_usage_db.linux_path = user_path
                self.db.commit()

            for user_id in exit_user_ids:
                self.db.query(StorageUsage).filter(StorageUsage.user_id == user_id,
                                                   StorageUsage.group_id == group_db.id).delete()
                self.logger.warning(f'Delete storage usages, user_id:{user_id} group_id:{group_db.id}')
            self.db.commit()
            ssh_client.close_ssh_connection()

    def collect_statistics_on_user_storage_usage(self):
        storage_usage_dbs = self.db.query(StorageUsage.user_id, func.sum(StorageUsage.used)).filter(
            StorageUsage.used > 0).group_by(
            StorageUsage.user_id).all()
        for storage_usage_db in storage_usage_dbs:
            user_id, storage_used = storage_usage_db
            user_db = self.db.query(User).filter_by(id=user_id).first()
            if user_db:
                if storage_used is not None:
                    user_db.storage_used = round(storage_used, 2)
                else:
                    user_db.storage_used = 0

        self.db.commit()

    def parse(self, output) -> Tuple[FileInfo, UserUid]:
        file_info = {}
        user_info = {}
        for line in output:
            if line.startswith('  File:'):
                file_info['File'] = line.split(':', 1)[1].strip()
            elif line.startswith('  Size:'):
                parts = line.split()
                file_info['Size'] = int(parts[1])
                file_info['Blocks'] = int(parts[3])
                file_info['IO Block'] = int(parts[6])
                file_info['Type'] = parts[7]
            elif line.startswith('Device:'):
                parts = line.split()
                file_info['Device'] = parts[1]
                file_info['Inode'] = parts[3]
                file_info['Links'] = int(parts[5])
            elif line.startswith('Access: ('):
                pattern = r'\(([^)]+)\)'
                matches = re.findall(pattern, line)
                file_info['Access'] = matches[0]
                uid_gid = matches[1].split('/')
                file_info['Gid'] = matches[2].replace(' ', '')
                user_info['rdUsername'] = uid_gid[1].strip()
                user_info['Uid'] = int(uid_gid[0].strip())
            elif line.startswith('Access: '):
                file_info['Access Time'] = line.split('Access: ', 1)[1].strip()
            elif line.startswith('Modify: '):
                file_info['Modify Time'] = line.split('Modify: ', 1)[1].strip()
            elif line.startswith('Change: '):
                file_info['Change Time'] = line.split('Change: ', 1)[1].strip()
            elif line.startswith(' Birth: '):
                file_info['Birth Time'] = line.split('Birth: ', 1)[1].strip()

            # 转换时间格式为标准北京时间
        file_info['Access Time'] = self.convert_to_beijing_time(file_info['Access Time'])
        file_info['Modify Time'] = self.convert_to_beijing_time(file_info['Modify Time'])
        file_info['Change Time'] = self.convert_to_beijing_time(file_info['Change Time'])
        file_info['Birth Time'] = self.convert_to_beijing_time(file_info['Birth Time'])
        return FileInfo(**file_info), UserUid(**user_info)

    @staticmethod
    def convert_to_beijing_time(time_str):
        # 时间字符串格式示例：2024-06-28 12:30:00.000000000 +0800
        if time_str:
            # 使用正则表达式提取时间部分
            match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.(\d+)( [+-]\d{4})', time_str)
            if match:
                dt_str = match.group(1)
                microseconds = match.group(2)[:6]  # 取前6位微秒
                tz_str = match.group(3)
                # 重新组合时间字符串
                time_str = f"{dt_str}.{microseconds} {tz_str}"
                # 解析为 datetime 对象
                dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f %z')
                # 转换时区到北京时间
                dt_beijing = dt.astimezone(timezone(timedelta(hours=8)))
                # 返回格式化的字符串
                return dt_beijing.strftime('%Y-%m-%d %H:%M:%S')
        return None


class StorageManagement:
    def __init__(self, db: Any, logger: Any):
        self.db = db
        self.logger = logger
        self.config = get_storage_config(db=self.db)
        self.ssh = self.create_ssh()
        self.email = EmailNotification(db=self.db, type='storage_usage')

    def create_ssh(self) -> SSHClientBase:
        hostname = self.config.storage_host
        port = self.config.storage_port if self.config.storage_port else 22
        username = self.config.storage_user
        password = self.config.storage_password
        return SSHClientBase(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            logger=self.logger
        )

    def clean_up(self) -> None:
        self.db.commit()
        self.ssh.close_ssh_connection()

    def add_email_company_info(self, data: Dict[str, Any], threshold: Optional[int] = None) -> Dict[str, Any]:
        data['company'] = self.config.company if self.config.company else "新华三半导体技术有限公司"
        data['domain_name'] = self.config.domain_name if self.config.domain_name else "http://localhost:5173"
        data[
            'personal_expand'] = self.config.person_expand if self.config.person_expand else ""
        data[
            'group_expand'] = self.config.group_expand if self.config.group_expand else ""
        if threshold:
            data['threshold'] = threshold
        return data

    def expand(self, expand_id: int, size: float, expand_type: str) -> None:
        if expand_type == StorageUsage.__name__:
            flag, message = self._expand_storage_usage(storage_usage_id=expand_id, size=size)
        elif expand_type == Group.__name__:
            flag, message = self._expand_group(group_id=expand_id, size=size)
        elif expand_type == Volume.__name__:
            flag, message = self._expand_volume(volume_id=expand_id, size=size)
        elif expand_type == Qtree.__name__:
            flag, message = self._expand_qtree(qtree_id=expand_id, size=size)
        else:
            flag, message = False, 'Invalid expand type'
        self._send_email(expand_id, size, flag, message, expand_type)
        self.clean_up()

    def _expand_storage_usage(self, storage_usage_id: int, size: float) -> Tuple[bool, str]:
        try:
            update_flag = False
            storage_usage_db = self.db.query(StorageUsage).filter_by(id=storage_usage_id).first()
            if storage_usage_db is None:
                return False, 'User path does not exist'

            qtree_name = storage_usage_db.group.qtree.name
            volume_name = storage_usage_db.group.qtree.volume.name
            rd_username = storage_usage_db.user.rd_username
            limit = round(storage_usage_db.limit / 1024, 2)
            size = limit + size
            show_flag, _ = self.ssh.execute_command(
                command=self.build_command(volume_name, qtree_name, rd_username, action='show')
            )

            if not show_flag:
                update_flag, message = self.ssh.execute_command(
                    command=self.build_command(volume_name, qtree_name, rd_username, size, action='create')
                )
            else:
                update_flag, message = self.ssh.execute_command(
                    command=self.build_command(volume_name, qtree_name, rd_username, size, action='modify')
                )
            if update_flag is True:
                resize_flag, resize_message = self.ssh.execute_command(
                    command=self.build_resize_command(volume_name=volume_name)
                )
                if resize_flag:
                    storage_usage_db.limit = size * 1024
                    self.db.commit()
                    self._create_alert(storage_usage_db.id, StorageUsage.__name__, limit, size,
                                       storage_usage_db.linux_path)
                    return True, str(message)

            return False, str(message)
        except Exception as e:
            self.logger.error(f"Error in expand: {e}")
            return False, str(e)

    def _expand_qtree(self, qtree_id: int, size: float) -> Tuple[bool, str]:
        qtree_db = self.db.query(Qtree).filter_by(id=qtree_id).first()
        if qtree_db is None:
            return False, 'Qtree does not exist'

        qtree_name = qtree_db.name
        volume_name = qtree_db.volume.name
        limit = round(qtree_db.limit / 1024, 2)
        size = limit + size
        show_flag, _ = self.ssh.execute_command(
            command=self.build_command(volume_name, 'null', qtree_name, action='show', type='qtree')
        )

        if not show_flag:
            created_flag, message = self.ssh.execute_command(
                command=self.build_command(volume_name, 'null', qtree_name, action='create', type='qtree')
            )
            if created_flag:
                qtree_db.limit = size * 1024
                self.db.commit()
                self._create_alert(qtree_db.id, Qtree.__name__, limit, size, qtree_db.name)
                return True, str(message)
        else:
            update_flag, message = self.ssh.execute_command(
                command=self.build_command(volume_name, 'null', qtree_name, size, action='modify', type='qtree')
            )
            if update_flag:
                resize_flag, resize_message = self.ssh.execute_command(
                    command=self.build_resize_command(volume_name=volume_name)
                )
                if resize_flag:
                    qtree_db.limit = size * 1024
                    self.db.commit()
                    self._create_alert(qtree_db.id, Qtree.__name__, limit, size, qtree_db.name)
                    return True, str(message)

        return False, str(message)

    def _expand_volume(self, volume_id: int, size: float) -> Tuple[bool, str]:
        volume_db = self.db.query(Volume).filter_by(id=volume_id).first()
        if volume_db is None:
            return False, 'Volume does not exist'

        volume_name = volume_db.name
        limit = round(volume_db.limit / 1024, 2)
        size = limit + size
        update_flag, message = self.ssh.execute_command(
            command=f"volume modify -vserver * -volume {volume_name} -size {size}t"
        )
        if update_flag:
            volume_db.limit = size * 1024
            self.db.commit()
            self._create_alert(volume_db.id, Volume.__name__, limit, size, volume_db.name)
            return True, str(message)

        return False, str(message)

    def _expand_group(self, group_id: int, size: float) -> Tuple[bool, str]:
        group_db = self.db.query(Group).filter_by(id=group_id).first()
        if group_db is None:
            return False, 'Group does not exist'

        resolved = resolve_group_storage_target(group_db)
        target = resolved["target"]
        if target is None:
            return False, 'Group storage target does not exist'
        if resolved["target_type"] == "qtree":
            flag, message = self._expand_qtree(qtree_id=target.id, size=size)
        else:
            flag, message = self._expand_volume(volume_id=target.id, size=size)
        if flag:
            limit = round(group_db.limit / 1024, 2)
            size = limit + size
            group_db.limit = size * 1024
            self.db.commit()
            self._create_alert(group_db.id, Group.__name__, limit, size, group_db.linux_path)
            return True, message

        return False, message

    def _create_alert(self, related_id: int, related_type: str, limit: float, size: float,
                      info: str | None = None) -> None:
        alert = StorageAlerts(
            alert_level='low',
            alert_type='expand',
            description=f"{info}从{limit}T扩容至{size}T",
            threshold=limit,
            avg_use_ratio=size,
            related_id=related_id,
            related_type=related_type,
            updated_at=datetime.now()
        )
        self.db.add(alert)

    def _send_email(self, related_id: int, size: float, flag: bool, message: str, expand_type: str) -> None:
        data = {
            'size': size,
            'flag': flag,
            'message': message.replace('\x08', '')
        }
        if expand_type == StorageUsage.__name__:
            storage_usage_db = self.db.query(StorageUsage).filter_by(id=related_id).first()
            storage_usages = storageUsageSchema.StorageUsage.from_orm(storage_usage_db).model_dump()
            data['storage_usages'] = storage_usages
            self.email.send_email_via_template(
                subject=f"【自动化扩容】【用户】【{storage_usage_db.linux_path}】结果反馈",
                recipient=[],
                data=self.add_email_company_info(data=data),
                template_name='userExpansionFeedback'
            )
        elif expand_type == Group.__name__:
            group_db = self.db.query(Group).filter_by(id=related_id).first()
            group_usages = groupSchema.Group.from_orm(group_db).model_dump()
            data['group_usages'] = group_usages
            self.email.send_email_via_template(
                subject=f"【自动化扩容】【项目组】【{group_db.linux_path}】结果反馈",
                recipient=[],
                data=self.add_email_company_info(data=data),
                template_name='groupExpansionFeedback'
            )

    @staticmethod
    def build_command(volume_name: str, qtree_name: str, name: str, size: float = 0, action: str = 'show',
                      type: str = 'user') -> str:
        command = f"volume quota policy rule {shlex.quote(action)}"
        if action != 'create':
            command += " -vserver '*'"
        command += f" -policy-name default -volume {shlex.quote(str(volume_name))}"
        if qtree_name != 'null':
            command += f' -qtree {shlex.quote(str(qtree_name))}'
        elif action == 'create' and qtree_name == 'null':
            command += " -qtree ''"
        if action != 'show':
            if 0 < size < 1:
                command += f" -disk-limit {int(1024 * size)}g"
            elif size >= 1:
                command += f" -disk-limit {size}t"
            else:
                command += " -disk-limit 10g"
        if type == 'user':
            command += f" -type {shlex.quote(type)} -target {shlex.quote(str(name))}"
        else:
            command += f" -target {shlex.quote(str(name))}"
        return command

    @staticmethod
    def build_resize_command(volume_name: str) -> str:
        return f"volume quota resize -vserver '*' -volume {shlex.quote(str(volume_name))}"
