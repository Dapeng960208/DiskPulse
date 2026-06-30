# -*- coding: utf-8 -*-
import asyncio
import functools
import logging

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from celery_tasks.manager.remoteFileManager import RemoteFileManager


def setup_logger(name="app:handle_exception"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def handle_exceptions(func):
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = setup_logger("app")
        try:
            return await func(*args, **kwargs)
        except ValidationError as exc:
            logger.error("ValidationError in %s: %s", func.__name__, exc)
            return JSONResponse(status_code=422, content={"detail": "Invalid data provided", "errors": exc.errors()})
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Exception in %s: %s", func.__name__, exc)
            return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "errors": str(exc)})

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = setup_logger("app")
        try:
            return func(*args, **kwargs)
        except ValidationError as exc:
            logger.error("ValidationError in %s: %s", func.__name__, exc)
            return JSONResponse(status_code=422, content={"detail": "Invalid data provided", "errors": exc.errors()})
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Exception in %s: %s", func.__name__, exc)
            return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "errors": str(exc)})

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def create_user_folder_by_storage_usage_id(db: Session, logger: logging.Logger, storage_usage_id: int):
    remote_file_manager = RemoteFileManager(db, logger)
    try:
        remote_file_manager.create_user_directory_and_assign_rights_by_storage_usage_id(
            storage_usage_id=storage_usage_id,
            permission="744",
        )
    finally:
        remote_file_manager.close_ssh_connection()


def back_up_user_storage_usage_by_storage_usage_id(
    db: Session,
    logger: logging.Logger,
    storage_usage_id: int,
    closed: bool = False,
):
    remote_file_manager = RemoteFileManager(db, logger)
    try:
        remote_file_manager.back_up_user_directory_by_storage_usage_id(
            storage_usage_id=storage_usage_id,
            closed=closed,
        )
    finally:
        remote_file_manager.close_ssh_connection()


def delete_storage_back_up_record_by_storage_usage_id(
    db: Session,
    logger: logging.Logger,
    storage_back_up_record_id: int,
):
    remote_file_manager = RemoteFileManager(db, logger)
    try:
        remote_file_manager.delete_back_up_destination_path_by_id(
            storage_back_up_record_id=storage_back_up_record_id,
        )
    finally:
        remote_file_manager.close_ssh_connection()


def rollback_storage_back_up_record_by_storage_usage_id(
    db: Session,
    logger: logging.Logger,
    storage_back_up_record_id: int,
):
    remote_file_manager = RemoteFileManager(db, logger)
    try:
        remote_file_manager.rollback_back_up_by_id(storage_back_up_record_id=storage_back_up_record_id)
    finally:
        remote_file_manager.close_ssh_connection()
