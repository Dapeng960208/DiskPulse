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
    dependencies=[Depends(require_super_admin)],
)


@router.get("/storage", response_model=configSchemas.StorageConfPublic)
def read_storage_config(db: Session = Depends(get_db)):
    return configCrud.get_storage_config(db=db)


@router.put("/storage", response_model=configSchemas.StorageConfPublic)
def update_storage_config(storage_config: configSchemas.StorageConf, db: Session = Depends(get_db)):
    return configCrud.update_storage_config(db=db, storage_config=storage_config)
