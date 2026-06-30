# -*- coding: utf-8 -*-
from dependencies import DBSession
from celery_worker import lsf_app
from celery_tasks.manager.storageMonitor import StoreMonitor, SynchronousPathState
from celery_tasks.manager.remoteFileManager import RemoteFileManager
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from celery_tasks.manager.storageAlert import StorageAlert
from celery_tasks.tasks.redis_lock import redis_lock
from celery.exceptions import SoftTimeLimitExceeded
from celery_tasks.manager.storagePulseMonitor import StoragePulseMonitor
from models import StorageCluster
logger = get_task_logger(__name__)


@lsf_app.task(soft_time_limit=120, time_limit=180, expires=60)
def storages_schedule_fetching_task():
    try:
        with redis_lock('storages_schedule_fetching_task_lock', expires=120) as have_lock:
            if have_lock:
                with DBSession() as db:
                    clusters = db.query(StorageCluster).filter(StorageCluster.is_active == True).all()
                    for cluster in clusters:
                        try:
                            monitor = StoragePulseMonitor(db, logger, storage_cluster_id=cluster.id)
                            monitor.start()
                        except Exception as e:
                            logger.error(f"Error monitoring cluster {cluster.name}: {e}")
            else:
                logger.info("Storages schedule fetching task is already running.")
    except Exception as e:
        logger.error(f"Error in storages fetching task: {e}")


@lsf_app.task(soft_time_limit=3000, time_limit=3000, expires=600)
def check_user_path_status_hourly():
    try:
        with DBSession() as db:
            sync_path = SynchronousPathState(db=db, logger=logger)
            sync_path.start()
    except Exception as e:
        logger.error(f"Error in Check user path status :{e}")


@lsf_app.task(soft_time_limit=120, time_limit=150, expires=1800)
def user_storage_usage_alert_hourly():
    with DBSession() as db:
        now = datetime.now()
        hour = int(now.hour)
        storage_alert = StorageAlert(db, logger)
        if hour == 8:
            storage_alert.user_alarm_hourly(threshold=80)
        else:
            storage_alert.user_alarm_hourly(threshold=95, end_time=datetime.now() - timedelta(minutes=3))


@lsf_app.task(soft_time_limit=300, time_limit=330, expires=1800)
def group_storage_usage_alert_hourly():
    with DBSession() as db:
        now = datetime.now()
        hour = int(now.hour)
        if hour == 8:
            storage_alert = StorageAlert(db, logger)
            storage_alert.group_alarm_daily(threshold=80)
            storage_alert.system_alarm_daily(threshold=80)
        else:
            storage_alert = StorageAlert(db, logger)
            storage_alert.group_alarm_daily(threshold=95, end_time=datetime.now() - timedelta(minutes=3))


@lsf_app.task(soft_time_limit=300, time_limit=330)
def project_storage_usage_report_weekly():
    with DBSession() as db:
        storage_alert = StorageAlert(db, logger)
        storage_alert.project_alarm_weekly()


@lsf_app.task(soft_time_limit=300, time_limit=330)
def group_quit_user_storage_usage_alert_weekly():
    with DBSession() as db:
        storage_alert = StorageAlert(db, logger)
        storage_alert.group_quit_user_alarm_weekly()


@lsf_app.task()
def quit_user_back_up_daily():
    with DBSession() as db:
        remote_file_manager = RemoteFileManager(db=db, logger=logger)
        remote_file_manager.initiating_quit_users_bpm_process()
        # remote_file_manager.back_up_quit_users_storage_usages()
        remote_file_manager.bacK_up_delete_alarm()
        remote_file_manager.delete_back_up()
        remote_file_manager.close_ssh_connection()
