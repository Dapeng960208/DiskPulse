# -*- coding: utf-8 -*-
from dependencies import DBSession
from celery_worker import diskpulse_app
from celery.utils.log import get_task_logger
from celery_tasks.manager.largeFileAlert import LargeFileAlert

logger = get_task_logger(__name__)


@diskpulse_app.task(soft_time_limit=300, time_limit=300, expires=300)
def user_large_files_alert_twice_monthly():
    with DBSession() as db:
        large_files = LargeFileAlert(db=db, logger=logger)
        large_files.send_weekly_large_file_alerts()
