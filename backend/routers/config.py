# -*- coding: utf-8 -*-
from fastapi import Depends
from sqlalchemy.orm import Session

from crud import configCrud
from dependencies import get_db, require_super_admin
from routers.transactional import TransactionalAPIRouter
from schemas import configSchemas

router = TransactionalAPIRouter(
    prefix="/config",
    tags=["config"],
    responses={404: {"description": "Not found"}},
)
AI_STORAGE_CONFIG_BLACKLIST_FIELDS = (
    "back_up_dir",
    "company",
    "domain_name",
    "file_manage_host",
    "file_manage_port",
    "file_manage_user",
    "group_expand",
    "mail_host",
    "mail_port",
    "mail_to",
    "mail_user",
    "person_expand",
)


@router.get(
    "/storage",
    response_model=configSchemas.StorageConfPublic,
    dependencies=[Depends(require_super_admin)],
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "get_storage_config",
        "ai_description": "查询存储系统设置",
        "ai_blacklist_fields": AI_STORAGE_CONFIG_BLACKLIST_FIELDS,
    },
)
def read_storage_config(db: Session = Depends(get_db)):
    return configCrud.get_storage_config(db=db)


@router.get(
    "/storage-alert-thresholds",
    response_model=configSchemas.StorageAlertThresholds,
)
def read_storage_alert_thresholds(db: Session = Depends(get_db)):
    rule = configCrud.get_storage_config(db=db).storage_alert_rule
    return {
        "important": rule.important.threshold,
        "serious": rule.serious.threshold,
        "emergency": rule.emergency.threshold,
    }


@router.put(
    "/storage",
    response_model=configSchemas.StorageConfPublic,
    dependencies=[Depends(require_super_admin)],
)
def update_storage_config(storage_config: configSchemas.StorageConf, db: Session = Depends(get_db)):
    return configCrud.update_storage_config(db=db, storage_config=storage_config)
