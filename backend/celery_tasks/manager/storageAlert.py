# -*- coding: utf-8 -*-

from models import (
    StorageUsage, Group, Project, Aggregate, Volume,
    Qtree, StorageAlerts, User,
)
from sqlalchemy import func, inspect as sa_inspect
from sqlalchemy.orm import joinedload
from crud.questDbCrud import get_high_avg_usage
from crud.configCrud import get_storage_config
from crud.groupCrud import serialize_group
from crud.storageUsageCrud import serialize_storage_usage
from utils.mailTools.emailNotification import EmailNotification
from schemas import storageUsageSchema, groupSchema, projectsSchema, aggregateSchema, volumeSchema, \
    qtreeSchema
from datetime import datetime, timedelta
from appConfig import base_config
from utils.storageTarget import resolve_group_storage_target


def _group_payload(group):
    return groupSchema.Group.model_validate(serialize_group(group)).model_dump()


def _storage_usage_payload(storage_usage):
    data = serialize_storage_usage(storage_usage)
    data["group"] = _group_payload(storage_usage.group)
    return storageUsageSchema.StorageUsage.model_validate(data).model_dump()


class StorageAlert:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
        self.config = get_storage_config(db=self.db)
        self.email = EmailNotification(db=self.db, type='storage_usage')
        self.model = base_config.get('application.mode')

    def add_email_company_info(self, data: dict, threshold=None):
        data['company'] = self.config.company if self.config.company else "新华三半导体技术有限公司"
        data['domain_name'] = self.config.domain_name if self.config.domain_name else "http://localhost:5173"
        data[
            'personal_expand'] = self.config.person_expand if self.config.person_expand else ""
        data[
            'group_expand'] = self.config.group_expand if self.config.group_expand else ""
        if threshold:
            data['threshold'] = threshold
        return data

    def get_user_alarm_data(self, threshold: int = 80,
                            end_time: datetime = datetime.now() - timedelta(hours=1)) -> dict:
        alarm_data = {}
        storage_usage_quest_dbs = get_high_avg_usage(
            table_prefix='storage_usage', storage_config=self.config, threshold=threshold, end_time=end_time
        )
        storage_usage_ids = {
            storage_usage_id for storage_usage_id, _avg_use_ratio in storage_usage_quest_dbs
        }
        storage_usage_dbs = self.db.query(StorageUsage).options(
            joinedload(StorageUsage.user),
            joinedload(StorageUsage.storage_cluster),
            joinedload(StorageUsage.group).joinedload(Group.project),
            joinedload(StorageUsage.group).joinedload(Group.storage_cluster),
            joinedload(StorageUsage.group).joinedload(Group.group_tag),
            joinedload(StorageUsage.group).joinedload(Group.volume),
            joinedload(StorageUsage.group).joinedload(Group.qtree).joinedload(Qtree.volume),
        ).join(
            Group, StorageUsage.group_id == Group.id
        ).filter(
            StorageUsage.id.in_(storage_usage_ids),
            Group.enable_monitoring.is_(True),
        ).all() if storage_usage_ids else []
        storage_usage_by_id = {
            storage_usage.id: storage_usage for storage_usage in storage_usage_dbs
        }
        for storage_usage_quest_db in storage_usage_quest_dbs:
            storage_usage_id, avg_use_ratio = storage_usage_quest_db
            storage_usage_db = storage_usage_by_id.get(storage_usage_id)
            if not storage_usage_db or storage_usage_db.user.is_alert is False:
                continue
            email = storage_usage_db.user.email or 'admin'
            if email not in alarm_data:
                alarm_data[email] = []
            alarm_data[email].append((storage_usage_db, avg_use_ratio))
        return alarm_data

    def user_alarm_hourly(self, threshold: int = 80, end_time: datetime = datetime.now() - timedelta(hours=1)):
        alarm_data = self.get_user_alarm_data(threshold=threshold, end_time=end_time)
        if len(alarm_data) == 0:
            self.logger.warning("No storage usages data")
            return

        result = []
        # 全局统计
        emergency_count = 0
        warning_count = 0
        important_count = 0

        for email, storage_dbs in alarm_data.items():
            try:
                # 统计该用户的告警级别
                emergency_in_user = 0
                warning_in_user = 0
                important_in_user = 0

                for _, avg_use_ratio in storage_dbs:
                    if avg_use_ratio >= 95:
                        emergency_in_user += 1
                        emergency_count += 1
                    elif avg_use_ratio >= 90:
                        warning_in_user += 1
                        warning_count += 1
                    elif avg_use_ratio >= 80:
                        important_in_user += 1
                        important_count += 1

                # 确定最高级别告警
                has_emergency = emergency_in_user > 0
                has_warning = warning_in_user > 0

                # 设置邮件主题
                if has_emergency:
                    subject = f"【紧急】用户存储使用告警 - 存储使用率超过95%"
                elif has_warning:
                    subject = f"【警告】用户存储使用告警 - 存储使用率超过90%"
                else:
                    subject = f"【重要】用户存储使用告警 - 存储使用率超过80%"

                if email != 'admin':
                    subject += f" (阈值:{threshold}%)"
                else:
                    subject = f"【重要】用户存储使用告警 [用户邮箱地址缺失]"

                # 设置收件人
                recipient = []
                if email != 'admin' and self.model != 'dev':
                    if len(email.split()) > 0:
                        recipient.extend(email.split())
                    else:
                        recipient.append(email.strip())
                else:
                    recipient = [email.strip() for email in (self.config.mail_to or "").split() if email.strip()]

                # 构建存储使用数据
                storage_usages = []
                for storage_db, avg_use_ratio in storage_dbs:
                    storage_dict = _storage_usage_payload(storage_db)
                    storage_dict['avg_use_ratio'] = round(avg_use_ratio, 2)

                    # 设置告警级别
                    if avg_use_ratio >= 95:
                        storage_dict['alert_level'] = '紧急'
                        storage_dict['alert_icon'] = '🔥'
                    elif avg_use_ratio >= 90:
                        storage_dict['alert_level'] = '警告'
                        storage_dict['alert_icon'] = '⚠️'
                    elif avg_use_ratio >= 80:
                        storage_dict['alert_level'] = '重要'
                        storage_dict['alert_icon'] = '❗'
                    else:
                        storage_dict['alert_level'] = ''
                        storage_dict['alert_icon'] = ''

                    storage_usages.append(storage_dict)

                # 添加告警统计信息到邮件数据
                user_data = {
                    'storage_usages': storage_usages,
                    'has_emergency': has_emergency,
                    'has_warning': has_warning,
                }

                self.email.send_email_via_template(
                    recipient=recipient, subject=subject,
                    data=self.add_email_company_info(data=user_data, threshold=threshold),
                    template_name='userAlarmHourly'
                )
                result += storage_dbs

            except Exception as e:
                self.logger.error(f"Error in user {email} alarm hourly :{e}")

        # 记录全局统计到日志
        if emergency_count > 0 or warning_count > 0 or important_count > 0:
            self.logger.warning(
                f"[User Alert Stats] 紧急:{emergency_count}, 警告:{warning_count}, 重要:{important_count}")

        self.write_alerts_to_mysql(data=result, model=StorageUsage, threshold=threshold,
                                   description_template="用户{name}使用率达到{avg_use_ratio}%")

    def get_project_group_alarm_data(self, threshold=90, end_time: datetime | None = None) -> dict:
        alarm_data = {}
        if end_time is None:
            end_time = datetime.now() - timedelta(days=1)
        storage_usage_quest_dbs = get_high_avg_usage(
            table_prefix='group', storage_config=self.config, threshold=threshold, end_time=end_time
        )
        group_ids = {group_id for group_id, _avg_use_ratio in storage_usage_quest_dbs}
        group_dbs = self.db.query(Group).options(
            joinedload(Group.project),
            joinedload(Group.storage_cluster),
            joinedload(Group.group_tag),
            joinedload(Group.volume),
            joinedload(Group.qtree).joinedload(Qtree.volume),
            joinedload(Group.in_charge_user),
        ).filter(
            Group.id.in_(group_ids),
            Group.enable_monitoring.is_(True),
        ).all() if group_ids else []
        group_by_id = {group.id: group for group in group_dbs}
        for storage_usage_quest_db in storage_usage_quest_dbs:
            group_id, avg_use_ratio = storage_usage_quest_db
            group_db = group_by_id.get(group_id)
            if not group_db or resolve_group_storage_target(group_db)["target"] is None:
                continue
            group_charge_email = group_db.in_charge_user.email if group_db.in_charge_user and group_db.in_charge_user.email else 'admin'
            if group_charge_email not in alarm_data:
                alarm_data[group_charge_email] = []
            alarm_data[group_charge_email].append((group_db, avg_use_ratio))
        return alarm_data

    def group_alarm_daily(self, threshold: int = 80, end_time: datetime | None = None):
        try:
            if end_time is None:
                end_time = datetime.now() - timedelta(days=1)
            alarm_data = self.get_project_group_alarm_data(threshold=threshold, end_time=end_time)
            if len(alarm_data) == 0:
                self.logger.warning("[Alert] No group data")
                return

            result = []
            # 统计紧急告警数量
            emergency_count = 0
            warning_count = 0
            important_count = 0
            group_ids = {
                sa_inspect(group_db).identity[0]
                for group_dbs in alarm_data.values()
                for group_db, _avg_use_ratio in group_dbs
            }
            ranked_usages = self.db.query(
                StorageUsage.id.label("storage_usage_id"),
                func.row_number().over(
                    partition_by=StorageUsage.group_id,
                    order_by=StorageUsage.used.desc(),
                ).label("usage_rank"),
            ).filter(
                StorageUsage.group_id.in_(group_ids),
                StorageUsage.used > 0,
            ).subquery()
            top_storage_usages = self.db.query(StorageUsage).options(
                joinedload(StorageUsage.user),
                joinedload(StorageUsage.group).joinedload(Group.project),
                joinedload(StorageUsage.group).joinedload(Group.storage_cluster),
                joinedload(StorageUsage.group).joinedload(Group.group_tag),
                joinedload(StorageUsage.group).joinedload(Group.volume),
                joinedload(StorageUsage.group).joinedload(Group.qtree).joinedload(Qtree.volume),
                joinedload(StorageUsage.group).joinedload(Group.in_charge_user),
            ).join(
                ranked_usages,
                ranked_usages.c.storage_usage_id == StorageUsage.id,
            ).filter(
                ranked_usages.c.usage_rank <= 20
            ).order_by(
                StorageUsage.group_id,
                StorageUsage.used.desc(),
            ).all() if group_ids else []
            top_usages_by_group = {}
            for storage_usage in top_storage_usages:
                top_usages_by_group.setdefault(storage_usage.group_id, []).append(
                    storage_usage
                )

            for email, group_dbs in alarm_data.items():
                try:
                    recipient = []
                    # 统计该邮件的告警级别
                    emergency_in_this_email = 0
                    warning_in_this_email = 0
                    important_in_this_email = 0

                    for _, avg_use_ratio in group_dbs:
                        if avg_use_ratio >= 95:
                            emergency_in_this_email += 1
                            emergency_count += 1
                        elif avg_use_ratio >= 90:
                            warning_in_this_email += 1
                            warning_count += 1
                        else:
                            important_in_this_email += 1
                            important_count += 1
        
                    # 确定最高级别告警
                    has_emergency = emergency_in_this_email > 0
                    has_warning = warning_in_this_email > 0

                    # 根据最高级别设置邮件主题
                    if has_emergency:
                        subject = f"【紧急】项目组存储超额告警 - 存储使用率超过95%"
                    elif has_warning:
                        subject = f"【警告】项目组存储超额告警 -  存储使用率超过90%"
                    else:
                        subject = f"【重要】项目组存储超额告警 - 存储使用率超过80%"

                    if email != 'admin':
                        subject += f" (阈值:{threshold}%)"
                    else:
                        subject = f"【重要】项目组存储告警 [未设置负责人或邮箱]"

                    if email != 'admin' and self.model != 'dev':
                        recipient.append(email)

                    group_usages = []
                    for group_db, avg_use_ratio in group_dbs:
                        if self.model != 'dev' and group_db.associated_mail_groups:
                            recipient += group_db.associated_mail_groups.split(',')

                        group_dict = _group_payload(group_db)
                        group_dict['avg_use_ratio'] = round(avg_use_ratio, 2)

                        # 设置告警级别
                        if avg_use_ratio >= 95:
                            group_dict['alert_level'] = '紧急'
                            group_dict['alert_icon'] = '🔥'
                        elif avg_use_ratio >= 90:
                            group_dict['alert_level'] = '警告'
                            group_dict['alert_icon'] = '⚠️'
                        elif avg_use_ratio >= 80:
                            group_dict['alert_level'] = '重要'
                            group_dict['alert_icon'] = '❗'
                        else:
                            group_dict['alert_level'] = ''
                            group_dict['alert_icon'] = ''

                        # 获取存储使用TOP20（保持原有逻辑）
                        group_id = sa_inspect(group_db).identity[0]
                        storage_usage_dbs = top_usages_by_group.get(group_id, [])

                        group_dict['storage_usages'] = [
                            _storage_usage_payload(storage_usage_db)
                            for storage_usage_db in storage_usage_dbs
                        ]

                        group_usages.append(group_dict)

                    # 添加告警统计信息
                    email_data = {
                        'group_usages': group_usages,
                        'has_emergency': has_emergency,
                        'has_warning': has_warning,
                        'emergency_count': emergency_in_this_email,
                        'warning_count': warning_in_this_email,
                        'important_count': important_in_this_email
                    }

                    self.email.send_email_via_template(
                        recipient=recipient, subject=subject,
                        data=self.add_email_company_info(data=email_data, threshold=threshold),
                        template_name='groupAlarmDaily'
                    )
                    result += group_dbs

                except Exception as e:
                    self.logger.error(f'Error in send mail:{e}')

            # 记录告警统计到日志
            if emergency_count > 0 or warning_count > 0 or important_count > 0:
                self.logger.warning(
                    f"[Alert Stats] 紧急:{emergency_count}, 警告:{warning_count}, 重要:{important_count}")

            self.write_alerts_to_mysql(data=result, model=Group, threshold=threshold,
                                       description_template="项目组{name}存储使用率达到{avg_use_ratio}%")

        except Exception as e:
            self.logger.error(f"Error in Group Alarm Daily : {e}")

    def get_project_group_quit_user_storage_usages(self):
        """
        每周一提醒quit_days内离职用户数据清理
        其他每天提醒离职时间等于quit_days的用户
        """
        quit_days = self.config.back_up_quit_days if self.config.back_up_quit_days else 30
        now = datetime.now()
        alarm_data = {}
        if now.weekday() == 0:
            storage_usage_dbs = self.db.query(StorageUsage).filter(StorageUsage.used > 0).join(User,
                                                                                               StorageUsage.user_id == User.id).filter(
                User.user_type == 0, User.quit_days < quit_days).join(Group, Group.id == StorageUsage.group_id).filter(
                Group.back_up_enabled == 1).all()
        else:
            storage_usage_dbs = self.db.query(StorageUsage).filter(StorageUsage.used > 0).join(User,
                                                                                               StorageUsage.user_id == User.id).filter(
                User.user_type == 0, User.quit_days == quit_days).join(Group, Group.id == StorageUsage.group_id).filter(
                Group.back_up_enabled == 1).all()
        for storage_usage_db in storage_usage_dbs:
            if storage_usage_db.group not in alarm_data:
                alarm_data[storage_usage_db.group] = []
            alarm_data[storage_usage_db.group].append(storage_usage_db)
        return alarm_data

    def write_alerts_to_mysql(self, data: list, model, threshold: int, description_template: str,
                              alert_type: str = 'alert'):
        alerts = []
        for related_db, avg_use_ratio in data:
            avg_use_ratio = round(avg_use_ratio, 2)
            alert_level = 'high' if avg_use_ratio >= 95 else 'medium' if avg_use_ratio >= 90 else 'low'
            description = description_template.format(
                name=related_db.linux_path if model.__name__ == StorageUsage.__name__ else related_db.name,
                avg_use_ratio=avg_use_ratio)
            related_info = None
            if model.__name__ == Group.__name__:
                project = related_db.project
                group_tag = related_db.group_tag
                description = f"{project.name}" + description
                related_info = {
                    "project": {"id": project.id, "name": project.name},
                    "group_tag": {"id": group_tag.id, "name": group_tag.name},
                    "group": {"id": related_db.id, "name": related_db.name},
                }
            related_id = related_db.id
            alert = StorageAlerts(
                alert_level=alert_level,
                alert_type=alert_type,
                description=description,
                threshold=threshold,
                avg_use_ratio=avg_use_ratio,
                related_id=related_id,
                related_type=model.__name__,
                related_info=related_info,
                updated_at=datetime.now()
            )
            alerts.append(alert)
        self.db.add_all(alerts)
        self.db.commit()
        self.logger.info(f'Write {model.__name__} Alerts {len(data)} to mysql')

    def project_alarm_weekly(self):
        alarm_data = self.get_project_alarm_data()
        project_ids = {
            project_db.id
            for project_dbs in alarm_data.values()
            for project_db, _avg_use_ratio in project_dbs
        }
        all_group_dbs = self.db.query(Group).options(
            joinedload(Group.project),
            joinedload(Group.storage_cluster),
            joinedload(Group.group_tag),
            joinedload(Group.qtree).joinedload(Qtree.volume),
            joinedload(Group.in_charge_user),
        ).filter(Group.project_id.in_(project_ids)).order_by(
            Group.project_id, Group.used.desc()
        ).all() if project_ids else []
        groups_by_project = {}
        for group_db in all_group_dbs:
            groups_by_project.setdefault(
                group_db.project_id, []
            ).append(group_db)
        result = []
        for email, project_dbs in alarm_data.items():
            try:
                recipient = []
                subject = "【重要】项目周报" if email != 'admin' else "【重要】项目周报 [未设置负责人或邮箱]"
                if email != 'admin' and self.model != 'dev':
                    recipient.append(email)
                else:
                    recipient.extend(email.strip() for email in (self.config.mail_to or "").split() if email.strip())
                project_usages = []
                for project_db, avg_use_ratio in project_dbs:
                    project_dict = projectsSchema.Project.model_validate(project_db).model_dump()
                    project_dict['avg_use_ratio'] = round(avg_use_ratio, 2)
                    group_dbs = groups_by_project.get(project_db.id, [])
                    group_usages = [_group_payload(group_db) for group_db in group_dbs]
                    tag_usages = {}
                    for group_db, group_usage in zip(group_dbs, group_usages):
                        group_tag = group_db.group_tag
                        section = tag_usages.setdefault(
                            group_tag.id,
                            {
                                'group_tag': {
                                    'id': group_tag.id,
                                    'name': group_tag.name,
                                },
                                'group_usages': [],
                            },
                        )
                        section['group_usages'].append(group_usage)
                    if self.model != 'dev':
                        recipient += [group_db.in_charge_user.email for group_db in group_dbs if
                                      group_db.in_charge_user and group_db.in_charge_user.email]
                    project_dict['group_usages'] = group_usages
                    project_dict['tag_usages'] = [
                        tag_usages[group_tag_id]
                        for group_tag_id in sorted(tag_usages)
                    ]
                    project_usages.append(project_dict)
                if len(project_usages) == 0:
                    continue
                data = {'project_usages': project_usages}
                self.email.send_email_via_template(
                    recipient=recipient, subject=subject,
                    data=self.add_email_company_info(data=data),
                    template_name='projectAlarmWeekly'
                )
                result += project_dbs
            except Exception as e:
                self.logger.error(f"Error in project weekly report {email} {e}")
        self.write_alerts_to_mysql(data=result, model=Project, threshold=0,
                                   description_template="项目{name}周报", alert_type='report')

    def get_project_alarm_data(self, end_time: datetime | None = None) -> dict:
        alarm_data = {}
        if end_time is None:
            end_time = datetime.now() - timedelta(days=7)
        project_quest_dbs = get_high_avg_usage(
            table_prefix='project', storage_config=self.config, threshold=0, end_time=end_time
        )
        project_ids = {project_id for project_id, _avg_use_ratio in project_quest_dbs}
        project_dbs = self.db.query(Project).options(
            joinedload(Project.in_charge_user)
        ).filter(Project.id.in_(project_ids)).all() if project_ids else []
        project_by_id = {project.id: project for project in project_dbs}
        for project_quest_db in project_quest_dbs:
            project_id, avg_use_ratio = project_quest_db
            project_db = project_by_id.get(project_id)
            if not project_db:
                continue
            project_charge_email = project_db.in_charge_user.email if project_db.in_charge_user and project_db.in_charge_user.email else 'admin'
            if project_charge_email not in alarm_data:
                alarm_data[project_charge_email] = []
            alarm_data[project_charge_email].append((project_db, avg_use_ratio))
        return alarm_data

    def get_system_alarm_data(self, end_time: datetime | None = None, threshold: int = 80):
        if end_time is None:
            end_time = datetime.now() - timedelta(days=1)
        aggregate_quest_dbs = get_high_avg_usage(
            table_prefix='aggregate', storage_config=self.config, threshold=threshold, end_time=end_time
        )
        volume_quest_dbs = get_high_avg_usage(
            table_prefix='volume', storage_config=self.config, threshold=threshold, end_time=end_time
        )
        qtree_quest_dbs = get_high_avg_usage(
            table_prefix='qtree', storage_config=self.config, threshold=threshold, end_time=end_time
        )
        return aggregate_quest_dbs, volume_quest_dbs, qtree_quest_dbs

    def system_alarm_daily(self, threshold: int = 80):
        try:
            aggregate_quest_dbs, volume_quest_dbs, qtree_quest_dbs = self.get_system_alarm_data(threshold=threshold)
            aggregate_usages, volume_usages, qtree_usages = [], [], []
            aggregate_result, volume_result, qtree_result = [], [], []
            aggregate_ids = {item_id for item_id, _ratio in aggregate_quest_dbs}
            volume_ids = {item_id for item_id, _ratio in volume_quest_dbs}
            qtree_ids = {item_id for item_id, _ratio in qtree_quest_dbs}
            aggregate_by_id = {
                item.id: item
                for item in self.db.query(Aggregate).options(
                    joinedload(Aggregate.storage_cluster)
                ).filter(Aggregate.id.in_(aggregate_ids)).all()
            } if aggregate_ids else {}
            volume_by_id = {
                item.id: item
                for item in self.db.query(Volume).options(
                    joinedload(Volume.storage_cluster)
                ).filter(Volume.id.in_(volume_ids)).all()
            } if volume_ids else {}
            qtree_by_id = {
                item.id: item
                for item in self.db.query(Qtree).options(
                    joinedload(Qtree.volume),
                    joinedload(Qtree.storage_cluster),
                ).filter(Qtree.id.in_(qtree_ids)).all()
            } if qtree_ids else {}

            # 处理聚合数据
            for aggregate_id, avg_use_ratio in aggregate_quest_dbs:
                aggregate_db = aggregate_by_id.get(aggregate_id)
                if aggregate_db is None:
                    continue
                aggregate_dict = aggregateSchema.Aggregate.model_validate(aggregate_db).model_dump()
                aggregate_dict['avg_use_ratio'] = round(avg_use_ratio, 2)

                # 添加警告标记
                if avg_use_ratio >= 95 and aggregate_db.used > 5:
                    aggregate_dict['high_warning'] = True
                    aggregate_dict['warning_message'] = "使用率超过95%，请及时展开文件清理工作或考虑扩容！"
                else:
                    aggregate_dict['high_warning'] = False
                    aggregate_dict['warning_message'] = ""

                aggregate_usages.append(aggregate_dict)
                aggregate_result.append((aggregate_db, avg_use_ratio))

            self.write_alerts_to_mysql(data=aggregate_result, model=Aggregate, threshold=threshold,
                                       description_template="聚合{name}使用率达到{avg_use_ratio}%")

            # 处理Volume数据
            for volume_id, avg_use_ratio in volume_quest_dbs:
                volume_db = volume_by_id.get(volume_id)
                if volume_db is None:
                    continue
                volume_dict = volumeSchema.Volume.model_validate(volume_db).model_dump()
                volume_dict['avg_use_ratio'] = round(avg_use_ratio, 2)

                # 获取当前使用率
                current_use_ratio = volume_dict.get('use_ratio', 0)

                # 添加警告标记
                if avg_use_ratio >= 95 or current_use_ratio >= 95:
                    volume_dict['high_warning'] = True
                    volume_dict['warning_message'] = "使用率超过95%，请检查关联项目使用存储，并立即开展清理工作！"
                else:
                    volume_dict['high_warning'] = False
                    volume_dict['warning_message'] = ""

                volume_usages.append(volume_dict)
                volume_result.append((volume_db, avg_use_ratio))

            self.write_alerts_to_mysql(data=volume_result, model=Volume, threshold=threshold,
                                       description_template="Volume {name}使用率达到{avg_use_ratio}%")

            # 处理Qtree数据
            for qtree_id, avg_use_ratio in qtree_quest_dbs:
                qtree_db = qtree_by_id.get(qtree_id)
                if qtree_db is None:
                    continue
                qtree_dict = qtreeSchema.Qtree.model_validate(qtree_db).model_dump()
                qtree_dict['avg_use_ratio'] = round(avg_use_ratio, 2)

                # 添加警告标记
                if avg_use_ratio >= 95:
                    qtree_dict['high_warning'] = True
                    qtree_dict['warning_message'] = "使用率超过95%，请督促用户进行文件清理或者考虑扩容！"
                else:
                    qtree_dict['high_warning'] = False
                    qtree_dict['warning_message'] = ""

                qtree_usages.append(qtree_dict)
                qtree_result.append((qtree_db, avg_use_ratio))

            self.write_alerts_to_mysql(data=qtree_result, model=Qtree, threshold=threshold,
                                       description_template="Qtree {name}存储使用率达到{avg_use_ratio}%")

            # 统计高使用率警告数量
            high_warning_count = sum(1 for item in aggregate_usages if item.get('high_warning', False))
            # high_warning_count += sum(1 for item in volume_usages if item.get('high_warning', False))
            # high_warning_count += sum(1 for item in qtree_usages if item.get('high_warning', False))

            data = {
                'aggregate_usages': aggregate_usages,
                'volume_usages': volume_usages,
                'qtree_usages': qtree_usages,
                'high_warning_count': high_warning_count,
                'has_high_warning': high_warning_count > 0
            }

            # 根据是否有高警告调整邮件主题
            if high_warning_count > 0:
                subject = f"【紧急】系统存储超额{threshold}%告警"
            else:
                subject = f"【重要】系统存储超额{threshold}%告警"

            self.email.send_email_via_template(
                recipient=[], subject=subject,
                data=self.add_email_company_info(data=data, threshold=threshold),
                template_name='systemAlarmDaily'
            )

        except Exception as e:
            self.logger.error(f"Error in system daily alarm {e}")
