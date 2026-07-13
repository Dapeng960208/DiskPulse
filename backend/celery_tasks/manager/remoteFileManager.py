# -*- coding: utf-8 -*-
from crud.configCrud import get_storage_config
from utils.sshClient import SSHClientBase
import os
import shlex
from models import StorageUsage, StorageBackUpRecord, User, Group
from datetime import datetime, timedelta
from schemas import storageBackUpRecordSchema
from utils.mailTools.emailNotification import EmailNotification
from sqlalchemy import and_, or_
from utils.iam.iamApi import IamApi
from appConfig import base_config


class RemoteFileManager:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
        self.storage_config = get_storage_config(db=self.db)
        self.client = self.create_ssh()
        self.email = EmailNotification(db=self.db, type='storage_usage')
        self.model = base_config.get('application.mode')

    def create_ssh(self):
        hostname = self.storage_config.file_manage_host
        port = self.storage_config.file_manage_port if self.storage_config.file_manage_port else 22
        username = self.storage_config.file_manage_user
        password = self.storage_config.file_manage_password
        return SSHClientBase(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            logger=self.logger
        )

    def add_email_company_info(self, data: dict):
        data['company'] = self.storage_config.company if self.storage_config.company else "新华三半导体技术有限公司"
        data[
            'domain_name'] = self.storage_config.domain_name if self.storage_config.domain_name else "http://localhost:5173"
        data[
            'personal_expand'] = self.storage_config.person_expand if self.storage_config.person_expand else ""
        data[
            'group_expand'] = self.storage_config.group_expand if self.storage_config.group_expand else ""
        return data

    def close_ssh_connection(self):
        self.client.close_ssh_connection()

    def execute_command(self, command):
        stdin, stdout, stderr = self.client.ssh.exec_command(command)
        return stdout.read().decode(), stderr.read().decode()

    @staticmethod
    def _shell_arg(value) -> str:
        return shlex.quote(str(value))

    @staticmethod
    def _permissions_arg(permissions) -> str:
        permissions = str(permissions)
        if not permissions.isdigit():
            raise ValueError("permissions must use numeric mode")
        return permissions

    def directory_exists(self, path):
        stdout, stderr = self.execute_command(f"test -d {self._shell_arg(path)} && echo exists")
        return "exists" in stdout

    def create_directory(self, path):
        stdout, stderr = self.execute_command(f"sudo mkdir -p {self._shell_arg(path)}")
        if stderr:
            self.logger.error(f"Error creating directory {path} : {stderr}")
            return False
        self.logger.info(f"Directory created: {path}")
        return True

    def change_permissions(self, path, permissions):
        stdout, stderr = self.execute_command(
            f"sudo chmod {self._permissions_arg(permissions)} -R {self._shell_arg(path)}"
        )
        if stderr:
            self.logger.error(f"Error changing permissions for {path} to {permissions}: {stderr}")
            return False
        self.logger.info(f"Permissions for {path} changed to {permissions}")
        return True

    def change_owner(self, path, user):
        stdout, stderr = self.execute_command(f"sudo chown {self._shell_arg(f'{user}:ic')} -R {self._shell_arg(path)}")
        if stderr:
            self.logger.error(f"Error changing owner of {path} to {user}: {stderr}")
            return False
        self.logger.info(f"Owner of {path} changed to {user}")
        return True

    def move_directory(self, source, destination):
        if not self.directory_exists(source):
            self.logger.warning(f"Source directory {source} does not exist.")
            return False
        if not self.directory_exists(destination):
            self.logger.warning(f"Destination directory {destination} does not exist.")
            return False

        stdout, stderr = self.execute_command(
            f"sudo mv -f {self._shell_arg(source)} {self._shell_arg(destination)}"
        )
        if stderr:
            self.logger.error(f"Error moving directory from {source} to {destination}: {stderr}")
            return False

        self.logger.info(f"Directory moved from {source} to {destination}")
        return True

    def rsync_directory(self, source, destination):
        if not self.directory_exists(source):
            self.logger.warning(f"Source directory {source} does not exist.")
            return False
        if not self.directory_exists(destination):
            self.logger.warning(f"Destination directory {destination} does not exist.")
            return False

        stdout, stderr = self.execute_command(
            f"sudo rsync -av --remove-source-files {self._shell_arg(source)} {self._shell_arg(destination)}"
        )
        if stderr:
            self.logger.error(f"Error syncing directory from {source} to {destination}: {stderr}")
            return False

        self.logger.info(f"Directory synced  from {source} to {destination}")
        return True

    def delete_directory(self, path, force=True):
        delete_command = f"sudo rm -rf {self._shell_arg(path)}" if force is True else f"sudo rm -r {self._shell_arg(path)}"
        if not self.directory_exists(path):
            self.logger.warning(f"Directory does not exist: {path}")
            return False
        stdout, stderr = self.execute_command(delete_command)
        if stderr:
            self.logger.error(f"Error deleting directory {path}: {stderr}")
            return False

        self.logger.info(f"Directory deleted: {path}")
        return True

    def create_user_directory_and_assign_rights_by_storage_usage_id(self, storage_usage_id, permission):
        storage_usage_db = self.db.query(StorageUsage).filter_by(id=storage_usage_id).first()
        if not storage_usage_db:
            return False
        rd_username = storage_usage_db.user.rd_username
        user_path = storage_usage_db.linux_path
        if not self.create_directory(user_path):
            return False
        if not self.change_owner(path=user_path, user=rd_username):
            return False
        if not self.change_permissions(path=user_path, permissions=permission):
            return False
        return True

    def _build_back_up_destination_path(self, storage_usage_db, back_up_dir):
        group = storage_usage_db.group
        if not group or not group.project:
            self.logger.warning("group or project not exited.")
            return False, None
        # delete space of project name
        project_name = group.project.name.replace(' ', '_')
        environment_name = (
            group.project_environment.name.replace(' ', '_')
            if group.project_environment is not None
            else None
        )
        group_name = group.name
        user_path = storage_usage_db.linux_path
        base_name = os.path.basename(user_path)
        path_parts = [back_up_dir, project_name]
        if environment_name is not None:
            path_parts.append(environment_name)
        group_back_dir = os.path.join(*path_parts, group_name)
        destination_path = os.path.join(group_back_dir, base_name)
        return destination_path

    def get_back_up_destination_path_by_id(self, storage_usage_id):
        back_up_dir = self.storage_config.back_up_dir
        if not back_up_dir:
            return None
        self.logger.info(f"Back up dir :{back_up_dir}")
        storage_usage_db = self.db.query(StorageUsage).filter_by(id=storage_usage_id).first()
        if not storage_usage_db:
            self.logger.warning("Storage not exited.")
            return False, None
        return self._build_back_up_destination_path(storage_usage_db, back_up_dir)

    def back_up_user_directory_by_storage_usage_id(self, storage_usage_id, closed=False):
        if not self.storage_config.back_up_enabled:
            self.logger.warning(
                "The project team disables the user backup function. Please check the project team Settings.")
            return False
        back_up_dir = self.storage_config.back_up_dir
        if not back_up_dir:
            return False, None
        storage_usage_db = self.db.query(StorageUsage).filter_by(id=storage_usage_id).first()
        if not storage_usage_db:
            self.logger.warning("Storage not exited.")
        user_path = storage_usage_db.linux_path
        destination_path = self._build_back_up_destination_path(storage_usage_db, back_up_dir)
        group_back_dir = os.path.dirname(destination_path)
        if not self.directory_exists(group_back_dir):
            if not self.create_directory(group_back_dir):
                self.logger.warnging(
                    f'Failed to create the backup directory {group_back_dir}')
                return False, None
            # 创建备份目录后修改权限
            self.change_owner(path=group_back_dir, user=self.storage_config.file_manage_user)
            self.change_permissions(path=group_back_dir, permissions=755)

        if not self.directory_exists(user_path):
            self.logger.warnging(
                f'User directory {user_path} not exit')
            return False, None
        start_time = datetime.now()
        storage_back_up_record = self.db.query(StorageBackUpRecord).filter(
            StorageBackUpRecord.source_path == user_path).first()
        status = 10 if closed is True else 1
        self.logger.info(f"status:{status},{storage_back_up_record is None} {destination_path}")
        if storage_back_up_record is None:
            storage_back_up_record = StorageBackUpRecord(source_path=user_path, destination_path=destination_path,
                                                         start_time=start_time, user_id=storage_usage_db.user_id,
                                                         end_time=start_time, status=status)
            self.db.add(storage_back_up_record)
        else:
            storage_back_up_record.status = status
            storage_back_up_record.start_time = start_time
            storage_back_up_record.end_time = start_time
        self.db.commit()
        # self.logger.info(f"status:{status},{storage_back_up_record is None} {destination_path}")
        if status == 10:
            return True, storage_back_up_record
        self.logger.info(f"Source path:{user_path} , destination path:{group_back_dir}")
        # if self.move_directory(source=user_path, destination=group_back_dir) is False:
        if self.rsync_directory(source=user_path, destination=group_back_dir) is False:
            storage_back_up_record.status = 0
            storage_back_up_record.end_time = datetime.now()
        else:
            if self.delete_directory(path=user_path, force=False) is False:
                storage_back_up_record.status = 0
                storage_back_up_record.end_time = datetime.now()
            else:
                storage_back_up_record.status = 2
                storage_back_up_record.end_time = datetime.now()
        self.db.commit()
        self.change_owner(path=destination_path, user=self.storage_config.file_manage_user)
        return True, storage_back_up_record

    def delete_back_up_destination_path_by_id(self, storage_back_up_record_id):
        storage_back_up_record_db = self.db.query(StorageBackUpRecord).filter(
            StorageBackUpRecord.id == storage_back_up_record_id).first()
        if not storage_back_up_record_db or storage_back_up_record_db.status != 2:
            return False
        back_up_dir = storage_back_up_record_db.destination_path
        storage_back_up_record_db.status = 4
        storage_back_up_record_db.start_time = datetime.now()
        storage_back_up_record_db.end_time = datetime.now()
        self.db.commit()
        delete_flag = self.delete_directory(path=back_up_dir)
        if delete_flag is True:
            storage_back_up_record_db.status = 5
        else:
            storage_back_up_record_db.status = 3
        storage_back_up_record_db.end_time = datetime.now()
        self.db.commit()
        return True

    def rollback_back_up_by_id(self, storage_back_up_record_id):
        storage_back_up_record_db = self.db.query(StorageBackUpRecord).filter(
            StorageBackUpRecord.id == storage_back_up_record_id).first()
        if not storage_back_up_record_db or storage_back_up_record_db.status != 2:
            return False

        source_path = storage_back_up_record_db.destination_path
        destination_path = os.path.dirname(storage_back_up_record_db.source_path)
        storage_back_up_record_db.status = 7
        storage_back_up_record_db.start_time = datetime.now()
        storage_back_up_record_db.end_time = datetime.now()
        self.db.commit()
        # if self.move_directory(source=source_path, destination=destination_path) is False:
        if self.rsync_directory(source=source_path, destination=destination_path) is False:
            storage_back_up_record_db.status = 6
        else:
            if self.delete_directory(path=source_path, force=False) is False:
                storage_back_up_record_db.status = 6
            else:
                storage_back_up_record_db.status = 8
        storage_back_up_record_db.end_time = datetime.now()
        self.db.commit()
        self.change_owner(path=storage_back_up_record_db.source_path, user=storage_back_up_record_db.user.rd_username)
        self.change_permissions(path=storage_back_up_record_db.source_path, permissions=744)
        return True

    def back_up_quit_users_storage_usages(self):
        if not self.storage_config.back_up_enabled:
            self.logger.warning(
                "The project team disables the user backup function. Please check the project team Settings.")
            return False
        quit_days = self.storage_config.back_up_quit_days if self.storage_config.back_up_quit_days else 30
        users = self.db.query(User).filter(User.user_type == 0, User.quit_days > quit_days).all()
        if len(users) == 0:
            self.logger.warning(
                "No user data need to be back up.")
            return
        storage_back_up_records = []
        for user in users:
            storage_usages_dbs = self.db.query(StorageUsage).join(Group, Group.id == StorageUsage.group_id).filter(
                StorageUsage.user_id == user.id, Group.back_up_enabled == 1).all()
            for storage_usages_db in storage_usages_dbs:
                linux_path = storage_usages_db.linux_path
                exit_record = self.db.query(StorageBackUpRecord).filter(StorageBackUpRecord.source_path == linux_path,
                                                                        StorageBackUpRecord.user_id == user.id,
                                                                        StorageBackUpRecord.status == 2).first()
                if exit_record:
                    self.logger.warning(f"Source path {linux_path} has been moved {exit_record.destination_path}")
                    continue
                move_flag, storage_back_up_record = self.back_up_user_directory_by_storage_usage_id(
                    storage_usage_id=storage_usages_db.id)
                if move_flag is False:
                    continue
                storage_back_up_records.append(
                    storageBackUpRecordSchema.StorageBackUpRecord.from_orm(storage_back_up_record).model_dump())
        if len(storage_back_up_records) == 0:
            self.logger.warning(
                "No data need to be back up.")
            return
        data = {}
        recipient = [email.strip() for email in (self.storage_config.mail_to or "").split() if email.strip()]
        subject = f"【重要】离职用户数据备份提醒"
        data['storage_back_up_records'] = storage_back_up_records
        data['quit_days'] = quit_days
        self.email.send_email_via_template(
            recipient=[], subject=subject,
            data=self.add_email_company_info(data=data),
            template_name='UserPathBackUpAlarm',
        )
        return True

    def bacK_up_delete_alarm(self):
        if not self.storage_config.back_up_enabled:
            self.logger.warning(
                "The project team disables the user backup function. Please check the project team Settings.")
            return False
        back_up_duration = self.storage_config.back_up_duration if self.storage_config.back_up_duration else 60
        start_time = datetime.now() - timedelta(days=back_up_duration)
        end_time = datetime.now() - timedelta(days=back_up_duration) + timedelta(days=7)
        storage_back_up_record_dbs = self.db.query(StorageBackUpRecord).filter(StorageBackUpRecord.status == 2,
                                                                               StorageBackUpRecord.end_time.between(
                                                                                   start_time, end_time)).all()
        storage_back_up_records = [
            storageBackUpRecordSchema.StorageBackUpRecord.from_orm(storage_back_up_record_db).model_dump() for
            storage_back_up_record_db in storage_back_up_record_dbs]
        if len(storage_back_up_record_dbs) == 0:
            self.logger.warning(
                "No storage back up records need to be deleted")
            return False
        for storage_back_up_record in storage_back_up_records:
            storage_back_up_record['duration'] = (datetime.now() - storage_back_up_record.get(
                'end_time')).days if storage_back_up_record.get('end_time') else 60
        data = {}
        recipient = [email.strip() for email in (self.storage_config.mail_to or "").split() if email.strip()]
        subject = f"【重要】数据备份即将删除提醒"
        data['storage_back_up_records'] = storage_back_up_records
        data['back_up_duration'] = back_up_duration
        self.email.send_email_via_template(
            recipient=[], subject=subject,
            data=self.add_email_company_info(data=data),
            template_name='BackUpToBeDeleteAlarm',
        )

    def delete_back_up(self):
        if not self.storage_config.back_up_enabled:
            self.logger.warning(
                "The project team disables the user backup function. Please check the project team Settings.")
            return False
        back_up_duration = self.storage_config.back_up_duration if self.storage_config.back_up_duration else 60
        start_time = datetime.now() - timedelta(days=back_up_duration)
        storage_back_up_record_dbs = self.db.query(StorageBackUpRecord).filter(StorageBackUpRecord.status == 2,
                                                                               StorageBackUpRecord.end_time < start_time).all()
        if len(storage_back_up_record_dbs) == 0:
            self.logger.warning(
                "No storage back up records  deleted")
            return False
        storage_back_up_records = []
        for storage_back_up_record_db in storage_back_up_record_dbs:
            self.delete_back_up_destination_path_by_id(storage_back_up_record_id=storage_back_up_record_db.id)
            new_storage_back_up_record_db = self.db.query(StorageBackUpRecord).filter(
                StorageBackUpRecord.id == storage_back_up_record_db.id).first()
            storage_back_up_records.append(
                storageBackUpRecordSchema.StorageBackUpRecord.from_orm(new_storage_back_up_record_db).model_dump())
        data = {}
        recipient = [email.strip() for email in (self.storage_config.mail_to or "").split() if email.strip()]
        subject = f"【重要】数据备份已删除提醒"
        data['storage_back_up_records'] = storage_back_up_records
        data['back_up_duration'] = back_up_duration
        self.email.send_email_via_template(
            recipient=[], subject=subject,
            data=self.add_email_company_info(data=data),
            template_name='BackUpDeletedAlarm',
        )

    def initiating_quit_users_bpm_process(self):
        """
        定期判断离职小于三十天的用户是否已离职，离职发起离职数据清理电子流
        :return:
        """
        if not self.storage_config.back_up_enabled:
            self.logger.warning(
                "The project team disables the user backup function. Please check the project team Settings.")
            return False
        quit_days = self.storage_config.back_up_quit_days if self.storage_config.back_up_quit_days else 30
        users = self.db.query(User).filter(User.user_type == 0, User.quit_days <= quit_days).all()
        iam = IamApi(db=self.db, logger=self.logger, type='storage')
        iam.set_up()
        if len(users) == 0:
            self.logger.warning(f'No quit users')
            return
        for user in users:
            storage_usage_dbs = self.db.query(StorageUsage).filter(StorageUsage.used > 0).join(User,
                                                                                               StorageUsage.user_id == user.id).join(
                Group,
                Group.id == StorageUsage.group_id).filter(
                Group.back_up_enabled == 1).all()
            # if user.rd_username != 'diskmonitor':
            #     continue
            if len(storage_usage_dbs) == 0:
                continue
            for storage_usage_db in storage_usage_dbs:
                if storage_usage_db.group is None or storage_usage_db.group.in_charge_user_id is None or storage_usage_db.linux_path is None:
                    self.logger.warning(
                        f"Storage usage ({storage_usage_db.id}) group is None or charge user is None or linux path is None")
                    continue
                user_path = storage_usage_db.linux_path
                if self.directory_exists(user_path) is False:
                    self.logger.warning(
                        f'User directory {user_path} not exit')
                    continue
                storage_back_up_record_db = self.db.query(StorageBackUpRecord).filter(
                    StorageBackUpRecord.source_path == user_path).first()
                if storage_back_up_record_db:
                    self.logger.warning(
                        f'Storage back up record {storage_back_up_record_db.id} exited ')
                    continue
                data = {
                    "formData": {
                        "groupId": storage_usage_db.group.id,
                        "rdUsernameId": user.id,
                        "storageUsageId": storage_usage_db.id,
                        "inChargeUserId": storage_usage_db.group.in_charge_user.iam_id
                    },
                }

                bpm_uid = iam.initiating_bpm_process(data=data)
                if bpm_uid is None:
                    continue
                destination_path = self.get_back_up_destination_path_by_id(storage_usage_id=storage_usage_db.id)
                start_time = datetime.now()
                storage_back_up_record = StorageBackUpRecord(source_path=user_path, destination_path=destination_path,
                                                             start_time=start_time, user_id=storage_usage_db.user_id,
                                                             end_time=start_time, status=9, process_uid=bpm_uid)
                self.db.add(storage_back_up_record)
                self.db.commit()
