# -*- coding: utf-8 -*-
from dependencies import DBSession
from celery_worker import lsf_app
from celery.utils.log import get_task_logger
from celery_tasks.manager.largeFileAlert import LargeFileAlert, LargeFileState

logger = get_task_logger(__name__)


@lsf_app.task(soft_time_limit=300, time_limit=300, expires=300)
def user_large_files_alert_twice_monthly():
    with DBSession() as db:
        large_files = LargeFileAlert(db=db, logger=logger)
        large_files.send_weekly_large_file_alerts()


@lsf_app.task(soft_time_limit=1800, time_limit=1800, expires=60)
def check_large_files_status_daily():
    with DBSession() as db:
        large_files = LargeFileState(db=db, logger=logger)
        large_files.execute_full_check_and_cleanup()
