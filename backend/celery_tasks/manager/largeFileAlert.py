# -*- coding: utf-8 -*-
# @Time      : 2025/12/1 15:08
# @Author    : guojianpeng
import csv
import tempfile
import os
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session
from models import StorageAlerts, User, LargeFiles, Group
from crud.configCrud import get_storage_config
from utils.mailTools.emailNotification import EmailNotification
from schemas import largeFileSchema
from appConfig import base_config
from utils.datetime_utils import utc_now


class LargeFileAlert:
    """大文件告警服务类，负责处理用户大文件的告警和邮件通知"""

    # 部门分类配置
    DEPARTMENT_CATEGORIES: dict[str, list[str]] = {}

    def __init__(self, db: Session, logger, model=None):
        self.db = db
        self.logger = logger
        self.storage_config = get_storage_config(db=self.db)
        self.email_service = EmailNotification(db=self.db, type='storage_usage')
        self.environment = base_config.get('application.mode', 'prod') if model is None else model

        # 常量定义
        self.DEV_EMAIL: list[str] = []
        self.MISSING_EMAIL_PLACEHOLDER = 'admin'
        self.ADMIN_EMAILS = self._get_admin_emails()

    def _get_admin_emails(self) -> List[str]:
        """获取管理员邮箱列表"""
        if self.environment == 'dev':
            return self.DEV_EMAIL

        # 生产环境从配置读取管理员邮箱
        if hasattr(self.storage_config, 'mail_to') and self.storage_config.mail_to:
            return [email.strip() for email in self.storage_config.mail_to.split() if email.strip()]

        self.logger.warning("No admin email configured")
        return []

    def _add_email_context(self, data: dict, threshold: int = None) -> dict:
        """为邮件模板添加上下文信息"""
        data['company'] = self.storage_config.company
        data['domain_name'] = self.storage_config.domain_name
        if threshold:
            data['threshold'] = threshold
        return data

    def _save_alerts_to_db(self, files: List[LargeFiles], threshold: int, alert_type: str = 'user') -> None:
        """将告警记录保存到数据库

        Args:
            files: 大文件列表
            threshold: 阈值(GB)
            alert_type: 告警类型，'user'为用户告警，'department'为部门告警
        """
        try:
            description = f"{threshold}G大文件清理提醒"
            if alert_type == 'department':
                description = f"{threshold}G大文件部门清理提醒"

            alerts = [
                StorageAlerts(
                    storage_cluster_id=(
                        file.group.storage_cluster_id if file.group is not None else None
                    ),
                    source="diskpulse",
                    fingerprint=f"diskpulse:large_file:{file.id}",
                    severity="critical",
                    alert_level='high',
                    alert_type='alert',
                    description=description,
                    threshold=threshold,
                    avg_use_ratio=threshold,
                    related_id=file.id,
                    related_type=LargeFiles.__name__,
                    updated_at=utc_now()
                )
                for file in files
            ]

            self.db.add_all(alerts)
            self.db.commit()
            self.logger.info(f"Saved {len(alerts)} {alert_type} large file alerts to DB")

        except Exception as e:
            self.logger.error(f"DB save failed: {e}")
            self.db.rollback()

    def _get_large_files_grouped_by_user(self, threshold_gb: int = 10) -> Dict[tuple, List[LargeFiles]]:
        """获取超过阈值的大文件并按用户邮箱分组"""
        try:
            # 查询超过阈值的大文件
            large_files = self.db.query(LargeFiles).filter(LargeFiles.size >= threshold_gb).all()

            if not large_files:
                self.logger.info(f"No large files found >= {threshold_gb}GB")
                return {}

            # 按用户分组
            files_by_user = {}

            for file in large_files:
                user = file.user
                user_email = user.email if user and user.email else self.MISSING_EMAIL_PLACEHOLDER
                rd_username = user.rd_username if user and user.rd_username else 'admin'

                # 如果 email 是缺失值，rd_username 也设为 admin
                if user_email == self.MISSING_EMAIL_PLACEHOLDER:
                    rd_username = 'admin'

                user_key = (user_email, rd_username)

                if user_key not in files_by_user:
                    files_by_user[user_key] = []

                files_by_user[user_key].append(file)

            self.logger.info(f"Found {len(large_files)} large files for {len(files_by_user)} users")
            return files_by_user

        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            return {}

    def _get_groups_by_department_category(self) -> Dict[str, List[Group]]:
        """按部门分类获取组列表"""
        groups_by_category = {}

        for dept_key in self.DEPARTMENT_CATEGORIES.keys():
            try:
                # 使用模糊搜索匹配组名
                groups = self.db.query(Group).filter(
                    Group.name.ilike(f'%{dept_key}%')
                ).all()

                if groups:
                    groups_by_category[dept_key] = groups
                    self.logger.info(f"Found {len(groups)} groups for department category '{dept_key}'")
                else:
                    groups_by_category[dept_key] = []
                    self.logger.warning(f"No groups found for department category '{dept_key}'")

            except Exception as e:
                self.logger.error(f"Failed to query groups for category '{dept_key}': {e}")
                groups_by_category[dept_key] = []

        return groups_by_category

    def _get_large_files_by_group_ids(self, group_ids: List[int], threshold_gb: int) -> List[LargeFiles]:
        """根据组ID列表获取大文件"""
        if not group_ids:
            return []

        try:
            files = self.db.query(LargeFiles).filter(
                LargeFiles.group_id.in_(group_ids),
                LargeFiles.size >= threshold_gb
            ).all()

            return files

        except Exception as e:
            self.logger.error(f"Failed to query large files by group ids: {e}")
            return []

    def _get_large_files_by_department_category(self, threshold_gb: int = 10) -> Dict[str, Dict[str, Any]]:
        """按部门分类获取大文件数据

        Returns:
            返回字典结构:
            {
                'de': {
                    'groups': [Group1, Group2, ...],
                    'files': [LargeFile1, LargeFile2, ...],
                    'group_ids': [1, 2, ...]
                },
                ...
            }
        """
        result = {}

        # 1. 按部门分类获取组
        groups_by_category = self._get_groups_by_department_category()

        # 2. 为每个部门分类获取大文件
        for dept_key, groups in groups_by_category.items():
            if not groups:
                continue

            # 获取组ID列表
            group_ids = [group.id for group in groups]

            # 获取该部门下所有组的大文件
            files = self._get_large_files_by_group_ids(group_ids, threshold_gb)

            if files:
                result[dept_key] = {
                    'groups': groups,
                    'files': files,
                    'group_ids': group_ids,
                    'group_count': len(groups),
                    'file_count': len(files)
                }
                self.logger.info(f"Found {len(files)} large files for department '{dept_key}' in {len(groups)} groups")
            else:
                self.logger.info(f"No large files found for department '{dept_key}'")

        return result

    def _create_csv_attachment(self, dept_key: str, dept_data: dict, threshold_gb: int) -> Optional[str]:
        """创建CSV格式的附件文件

        Args:
            dept_key: 部门标识
            dept_data: 部门数据
            threshold_gb: 阈值大小

        Returns:
            CSV文件路径，如果创建失败则返回None
        """
        if not dept_data.get('files'):
            return None

        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', encoding='gbk',
                                             suffix='.csv', delete=False) as temp_file:
                csv_path = temp_file.name

                # 创建CSV写入器
                writer = csv.writer(temp_file)

                # 写入标题行
                headers = ['文件路径', '文件大小(GB)',
                           '文件类型', '文件更新时间',
                           '项目组负责人', '用户',
                           ]
                writer.writerow(headers)

                # 写入数据行
                for file in dept_data['files']:
                    # 获取组信息
                    group_leader = '无'
                    if file.group:
                        if file.group.in_charge_user:
                            group_leader = f"{file.group.in_charge_user.rd_username or ''} {file.group.in_charge_user.username or ''}" or '无'

                    # 获取用户信息
                    username = '未知用户'
                    if file.user:
                        username = f"{file.user.rd_username or ''} {file.user.username or ''}" or '未知用户'

                    # 格式化文件路径
                    linux_path = file.linux_path or '未知路径'

                    updated_at = file.updated_at.strftime('%Y-%m-%d %H:%M:%S') if file.updated_at else '未知'

                    # 写入一行数据
                    row = [
                        linux_path,
                        f"{file.size:.1f}",
                        file.file_type or '未知',
                        updated_at,
                        group_leader,
                        username,
                    ]
                    writer.writerow(row)

                self.logger.info(f"Created CSV attachment for department '{dept_key}': {csv_path}")
                return csv_path

        except Exception as e:
            self.logger.error(f"Failed to create CSV attachment for department '{dept_key}': {e}")
            return None

    def _prepare_department_email_data(self, dept_key: str, dept_data: dict, threshold_gb: int) -> dict:
        """准备部门邮件数据"""
        # 获取统计数据
        file_count = dept_data.get('file_count', 0)
        group_count = dept_data.get('group_count', 0)

        # 获取责任人邮箱
        cc_emails = set()
        for group in dept_data['groups']:
            if group.in_charge_user and group.in_charge_user.email:
                emails = group.in_charge_user.email.split()
                for email in emails:
                    if email.strip():
                        cc_emails.add(email.strip())

        # 计算总大小
        total_size_gb = sum(file.size for file in dept_data['files']) if dept_data.get('files') else 0

        return {
            'department_category': dept_key.upper(),
            'group_count': group_count,
            'file_count': file_count,
            'total_size_gb': f"{total_size_gb:.2f}",
            'threshold': threshold_gb,
            'cc_emails': list(cc_emails) if cc_emails else [],
            'has_attachment': True,  # 标记有附件
            'attachment_info': f"{dept_key.upper()}_department_large_files_{utc_now().strftime('%Y%m%d')}.csv"
        }

    def _rename_file_with_timestamp(self, file_path, prefix_name):
        # 获取文件所在目录和原始扩展名
        dir_name = os.path.dirname(file_path)
        _, ext = os.path.splitext(file_path)

        # 生成当前时间戳（年月日时分秒）
        timestamp = utc_now().strftime("%Y%m%d%H%M%S")

        # 构造新文件名
        new_file_name = f"{prefix_name}_{timestamp}{ext}"
        new_file_path = os.path.join(dir_name, new_file_name)
        try:
            os.rename(file_path, new_file_path)
            return new_file_path
        except OSError as e:
            self.logger.error(f"Rename failed:{e}")
            return None

    def _send_department_email(self, dept_key: str, dept_data: dict, threshold_gb: int) -> bool:
        """发送部门大文件告警邮件

        主送：部门分类对应的邮箱
        抄送：组责任人邮箱
        附件：部门大文件详细数据CSV文件
        """
        csv_path = None
        try:
            # 1. 创建CSV附件
            csv_path = self._create_csv_attachment(dept_key, dept_data, threshold_gb)

            # 2. 获取主送邮箱
            to_email = self.DEPARTMENT_CATEGORIES.get(dept_key)
            if not to_email:
                self.logger.error(f"No email configured for department category '{dept_key}'")
                if csv_path and os.path.exists(csv_path):
                    os.remove(csv_path)
                return False
            csv_path = self._rename_file_with_timestamp(csv_path, dept_key)
            # 3. 准备邮件数据
            email_data = self._prepare_department_email_data(dept_key, dept_data, threshold_gb)
            email_context = self._add_email_context(email_data, threshold_gb)

            # 4. 获取抄送邮箱列表
            cc_emails = email_data['cc_emails']

            # 5. 生成邮件主题
            subject_prefix = "[DEV] " if self.environment == 'dev' else ""
            current_date = utc_now().strftime('%Y-%m-%d')
            subject = f"{subject_prefix}{dept_key.upper()}部门大文件清理提醒 - {current_date}"

            # 6. 添加环境信息
            email_context['environment'] = self.environment

            # 8. 开发环境特殊处理
            if self.environment == 'dev':
                # 开发环境只发送给管理员
                to_recipients = self.ADMIN_EMAILS
                cc_recipients = []
                self.logger.info(f"DEV environment: Sending department email to admins instead of {to_email}")
            else:
                # 生产环境：主送部门邮箱，抄送责任人
                to_recipients = to_email.split() if isinstance(to_email, str) else to_email
                cc_recipients = cc_emails

            # 9. 发送邮件（带附件）
            self.logger.info(f"Sending department email for '{dept_key}' with attachments: {csv_path}")

            # 检查 EmailNotification 的 send_email_via_template 方法支持的参数
            self.email_service.send_email_via_template(
                to=to_recipients,
                cc=cc_recipients if cc_recipients else None,
                subject=subject,
                data=email_context,
                template_name='DepartmentLargeFiles',
                attachments=csv_path  # 直接传递附件列表
            )

            self.logger.info(
                f"Department email sent for '{dept_key}' -> TO: {to_recipients}, CC: {cc_recipients}")
            return True

        except Exception as e:
            self.logger.error(f"Department email failed for '{dept_key}': {str(e)}", exc_info=True)
            return False

        finally:
            # 清理临时文件
            if csv_path and os.path.exists(csv_path):
                try:
                    os.remove(csv_path)
                    self.logger.info(f"Cleaned up temporary CSV file: {csv_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup temporary file {csv_path}: {e}")

    def _prepare_email_data_for_user(self, user_files: List[LargeFiles], threshold_gb: int, user_email: str) -> dict:
        """准备邮件数据，包含用户邮箱信息"""
        formatted_files = []
        for file in user_files:
            file_data = largeFileSchema.LargeFileList.model_validate(file).model_dump()
            file_data['threshold'] = threshold_gb
            formatted_files.append(file_data)

        return {
            'user_large_files': formatted_files,
            'target_user_email': user_email
        }

    def _get_email_recipients(self, user_email: str) -> List[str]:
        """获取邮件收件人列表"""
        if self.environment == 'dev':
            return self.ADMIN_EMAILS
        else:
            if user_email == self.MISSING_EMAIL_PLACEHOLDER:
                return self.ADMIN_EMAILS
            return user_email.split() if ' ' in user_email else [user_email.strip()]

    def _get_email_subject(self, user_email: str) -> str:
        """生成邮件主题"""
        if self.environment == 'dev':
            if user_email == self.MISSING_EMAIL_PLACEHOLDER:
                return f"[DEV] 用户大文件清理提醒 [用户邮箱缺失]"
            return f"[DEV] 用户大文件清理提醒 - 实际用户: {user_email}"
        else:
            if user_email == self.MISSING_EMAIL_PLACEHOLDER:
                return "用户大文件清理提醒 [用户邮箱地址缺失]"
            return "用户大文件清理提醒"

    def _send_email_to_user(self, user_key: tuple, user_files: List[LargeFiles], threshold_gb: int) -> bool:
        """给单个用户（或管理员）发送大文件告警邮件"""
        try:
            user_email, rd_username = user_key
            recipients = self._get_email_recipients(user_email)
            if not recipients:
                self.logger.warning("No recipient configured for large file alert")
                return False
            subject = self._get_email_subject(user_email)

            email_data = self._prepare_email_data_for_user(user_files, threshold_gb, user_email)
            email_context = self._add_email_context(email_data, threshold_gb)
            email_context['environment'] = self.environment
            email_context['rd_username'] = rd_username
            self.email_service.send_email_via_template(
                to=recipients,
                subject=subject,
                data=email_context,
                template_name='LargeFilesTwiceMonthly'
            )

            self.logger.info(f"Email sent for user {user_email} -> recipients: {recipients}")
            return True

        except Exception as e:
            self.logger.error(f"Email failed for user {user_email}: {e}")
            return False

    def send_weekly_large_file_alerts(self, threshold_gb: int = 10) -> None:
        """
        发送每周大文件告警邮件（包含用户告警和部门告警）

        Args:
            threshold_gb: 文件大小阈值（GB），默认10GB
        """
        self.logger.info(
            f"Starting weekly large file alert check (threshold: {threshold_gb}GB, env: {self.environment})")

        # 1. 发送用户大文件告警（原有功能）
        user_files_by_email = self._get_large_files_grouped_by_user(threshold_gb)

        if user_files_by_email:
            user_success_count = 0
            all_user_files = []

            for user_key, user_files in user_files_by_email.items():
                if self._send_email_to_user(user_key, user_files, threshold_gb):
                    user_success_count += 1
                    all_user_files.extend(user_files)

            if all_user_files:
                self._save_alerts_to_db(all_user_files, threshold_gb, 'user')

            self.logger.info(
                f"User alerts: {user_success_count}/{len(user_files_by_email)} users, {len(all_user_files)} files")
        else:
            self.logger.info("No user large files to process")

        # 2. 发送部门大文件告警（新增功能，带附件）
        dept_files_data = self._get_large_files_by_department_category(threshold_gb)

        if dept_files_data:
            dept_success_count = 0
            all_dept_files = []

            for dept_key, dept_data in dept_files_data.items():
                if self._send_department_email(dept_key, dept_data, threshold_gb):
                    dept_success_count += 1
                    all_dept_files.extend(dept_data['files'])

            if all_dept_files:
                self._save_alerts_to_db(all_dept_files, threshold_gb, 'department')

            self.logger.info(
                f"Department alerts: {dept_success_count}/{len(dept_files_data)} departments, {len(all_dept_files)} files")
        else:
            self.logger.info("No department large files to process")

        self.logger.info("Weekly large file alert process completed")

    def send_department_alerts_only(self, threshold_gb: int = 10) -> None:
        """
        只发送部门告警邮件（可选功能）

        Args:
            threshold_gb: 文件大小阈值（GB）
        """
        self.logger.info(f"Starting department-only alerts (threshold: {threshold_gb}GB)")

        dept_files_data = self._get_large_files_by_department_category(threshold_gb)

        if dept_files_data:
            dept_success_count = 0
            all_dept_files = []

            for dept_key, dept_data in dept_files_data.items():
                if self._send_department_email(dept_key, dept_data, threshold_gb):
                    dept_success_count += 1
                    all_dept_files.extend(dept_data['files'])

            if all_dept_files:
                self._save_alerts_to_db(all_dept_files, threshold_gb, 'department')

            self.logger.info(
                f"Department-only alerts: {dept_success_count}/{len(dept_files_data)} departments, {len(all_dept_files)} files")
        else:
            self.logger.info("No department large files to process")
