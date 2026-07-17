# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crud import configCrud
from dependencies import get_db, require_super_admin
from schemas import configSchemas

router = APIRouter(
    prefix="/config",
    tags=["config"],
    responses={404: {"description": "Not found"}},
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
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "update_storage_config",
        "ai_description": "更新存储系统设置",
    },
)
def update_storage_config(storage_config: configSchemas.StorageConf, db: Session = Depends(get_db)):
    return configCrud.update_storage_config(db=db, storage_config=storage_config)
