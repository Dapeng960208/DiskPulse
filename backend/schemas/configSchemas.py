# -*- coding: utf-8 -*-
from pydantic import BaseModel, ConfigDict
from schemas.storageAlertRuleSchema import DEFAULT_STORAGE_ALERT_RULE, StorageAlertRule


class StorageConf(BaseModel):
    id: int | None = None
    name: str | None = None
    mail_host: str | None = None
    mail_port: int = 587
    mail_to: str | None = None
    mail_user: str | None = None
    mail_password: str | None = None
    domain_name: str | None = None
    person_expand: str | None = None
    group_expand: str | None = None
    company: str | None = None
    file_manage_host: str | None = None
    file_manage_port: int | None = 22
    file_manage_user: str | None = None
    file_manage_password: str | None = None
    back_up_enabled: bool | None = False
    back_up_dir: str | None = None
    back_up_duration: int | None = 60
    back_up_quit_days: int | None = 30
    storage_alert_rule: StorageAlertRule = StorageAlertRule.model_validate(DEFAULT_STORAGE_ALERT_RULE)

    model_config = ConfigDict(from_attributes=True)


class StorageConfPublic(BaseModel):
    id: int | None = None
    name: str | None = None
    mail_host: str | None = None
    mail_port: int = 587
    mail_to: str | None = None
    mail_user: str | None = None
    domain_name: str | None = None
    person_expand: str | None = None
    group_expand: str | None = None
    company: str | None = None
    file_manage_host: str | None = None
    file_manage_port: int | None = 22
    file_manage_user: str | None = None
    back_up_enabled: bool | None = False
    back_up_dir: str | None = None
    back_up_duration: int | None = 60
    back_up_quit_days: int | None = 30
    storage_alert_rule: StorageAlertRule = StorageAlertRule.model_validate(DEFAULT_STORAGE_ALERT_RULE)

    model_config = ConfigDict(from_attributes=True)
