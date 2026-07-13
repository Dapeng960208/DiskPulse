# -*- coding: utf-8 -*-

from models import StorageUsage, Group, Project, Aggregate, Volume, Qtree, StorageAlerts, User
from crud.questDbCrud import get_high_avg_usage
from crud.configCrud import get_storage_config
from utils.mailTools.emailNotification import EmailNotification
from schemas import storageUsageSchema, groupSchema, projectsSchema, aggregateSchema, volumeSchema, \
    qtreeSchema
from datetime import datetime, timedelta
from appConfig import base_config


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
        for storage_usage_quest_db in storage_usage_quest_dbs:
            storage_usage_id, avg_use_ratio = storage_usage_quest_db
            storage_usage_db = self.db.query(StorageUsage).filter(
                StorageUsage.id == storage_usage_id).first()
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
                    storage_dict = storageUsageSchema.StorageUsage.model_validate(storage_db).model_dump()
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
        for storage_usage_quest_db in storage_usage_quest_dbs:
            group_id, avg_use_ratio = storage_usage_quest_db
            group_db = self.db.query(Group).filter(Group.id == group_id, Group.qtree_id.isnot(None)).first()
            if not group_db:
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

            for email, group_dbs in alarm_data.items():
                try:
                    recipient = []
                    # 统计该邮件的告警级别
                    emergency_in_this_email = 0
                    warning_in_this_email = 0

                    for _, avg_use_ratio in group_dbs:
                        if avg_use_ratio >= 95:
                            emergency_in_this_email += 1
                            emergency_count += 1
                        elif avg_use_ratio >= 90:
                            warning_in_this_email += 1
                            warning_count += 1
        
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

                        group_dict = groupSchema.Group.model_validate(group_db).model_dump()
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
                        storage_usage_dbs = self.db.query(StorageUsage).filter(
                            StorageUsage.group_id == group_db.id, StorageUsage.used > 0
                        ).order_by(StorageUsage.used.desc()).limit(20).all()

                        group_dict['storage_usages'] = [
                            storageUsageSchema.StorageUsage.model_validate(storage_usage_db).default_dict()
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

    # def group_quit_user_alarm_weekly(self):
    #     alarm_data = self.get_project_group_quit_user_storage_usages()
    #     if len(alarm_data) == 0:
    #         self.logger.warning("[Alert] No group quit user to alert")
    #         return
    #     quit_days = self.config.back_up_quit_days if self.config.back_up_quit_days else 30
    #     for group_db, storage_usages_dbs in alarm_data.items():
    #         data = {'group_usage': groupSchema.Group.model_validate(group_db).model_dump()}
    #         email = group_db.in_charge_user.email
    #         subject = f"[{group_db.project.name}]-[{group_db.name}] 离职用户存储数据清理 "
    #         # if self.model != 'dev':
    #         #     recipient.append(email)
    #         data['storage_usages'] = [
    #             storageUsageSchema.StorageUsage.model_validate(storage_usage_db).default_dict()
    #             for storage_usage_db in storage_usages_dbs
    #         ]
    #         data['quit_days'] = quit_days
    #         self.email.send_email_via_template(
    #             recipient=recipient, subject=subject,
    #             data=self.add_email_company_info(data=data),
    #             template_name='groupQuitUserAlarmWeekly'
    #         )

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
            if model.__name__ == Group.__name__:
                description = f"{related_db.project.name}" + description
            related_id = related_db.id
            alert = StorageAlerts(
                alert_level=alert_level,
                alert_type=alert_type,
                description=description,
                threshold=threshold,
                avg_use_ratio=avg_use_ratio,
                related_id=related_id,
                related_type=model.__name__,
                updated_at=datetime.now()
            )
            alerts.append(alert)
        self.db.add_all(alerts)
        self.db.commit()
        self.logger.info(f'Write {model.__name__} Alerts {len(data)} to mysql')

    def project_alarm_weekly(self):
        alarm_data = self.get_project_alarm_data()
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
                    group_dbs = self.db.query(Group).filter(Group.project_id == project_db.id,
                                                            Group.qtree_id.isnot(None)).order_by(
                        Group.used.desc()).all()
                    group_usages = [groupSchema.Group.model_validate(group_db).model_dump() for group_db in group_dbs]
                    if self.model != 'dev':
                        recipient += [group_db.in_charge_user.email for group_db in group_dbs if
                                      group_db.in_charge_user and group_db.in_charge_user.email]
                    project_dict['group_usages'] = group_usages
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
        for project_quest_db in project_quest_dbs:
            project_id, avg_use_ratio = project_quest_db
            project_db = self.db.query(Project).filter(Project.id == project_id).first()
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

            # 处理聚合数据
            for aggregate_id, avg_use_ratio in aggregate_quest_dbs:
                aggregate_db = self.db.query(Aggregate).filter_by(id=aggregate_id).first()
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
                volume_db = self.db.query(Volume).filter_by(id=volume_id).first()
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
                qtree_db = self.db.query(Qtree).filter_by(id=qtree_id).first()
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
