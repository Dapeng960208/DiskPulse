# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session

from models import StorageConf
from schemas import configSchemas


def get_storage_config(db: Session) -> configSchemas.StorageConf:
    config_db = db.query(StorageConf).first()
    if config_db is None:
        config_db = StorageConf(name="storage conf")
        db.add(config_db)
        db.commit()
        db.refresh(config_db)
    return configSchemas.StorageConf.model_validate(config_db)


def update_storage_config(db: Session, storage_config: configSchemas.StorageConf):
    storage_config_db = db.query(StorageConf).first()
    if storage_config_db is None:
        storage_config_db = StorageConf(name="storage conf")
        db.add(storage_config_db)

    update_data = storage_config.model_dump(exclude={"id"}, exclude_unset=True)
    for key, value in update_data.items():
        setattr(storage_config_db, key, value)

    db.commit()
    db.refresh(storage_config_db)
    return storage_config_db
