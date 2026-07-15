# -*- coding: utf-8 -*-
from celery import Celery
import os
import redis
from celery.schedules import crontab
from appConfig import base_config

redis_ip = base_config.get('redis.host')
diskpulse_app = Celery(
    "diskpulse_app",
    broker=f"redis://{redis_ip}:6379/5",
    backend=f"redis://{redis_ip}:6379/6",
)

redis_client = redis.StrictRedis(host=redis_ip, port=6379, db=7)
diskpulse_app.conf.update(
    timezone='Asia/Shanghai',
    enable_utc=False,
    broker_connection_retry_on_startup=True,
    task_default_queue='cad_manager_queue',
    task_default_exchange='cad_manager_exchange',
    task_default_routing_key='cad_manager_routing_key',
    result_expires=600
)
diskpulse_app.conf.beat_schedule = {
    # "hosts_schedule_fetching_task": {
    #     "task": "celery_tasks.tasks.hosts.hosts_schedule_fetching_task",
    #     "schedule": 60.0,
    #     "options": {"expires": 60},
    # },
    # "jobs_schedule_fetching_task": {
    #     "task": "celery_tasks.tasks.jobs.jobs_schedule_fetching_task",
    #     "schedule": 60.0,
    #     "options": {"expires": 60},
    # },
    "storages_schedule_fetching_task": {
        "task": "celery_tasks.tasks.storages.storages_schedule_fetching_task",
        "schedule": 60.0,
        "options": {"expires": 120},
    },
    "storage_events_schedule_fetching_task": {
        "task": "celery_tasks.tasks.storage_health.storage_events_schedule_fetching_task",
        "schedule": 60.0,
        "options": {"expires": 60},
    },
    "storage_performance_schedule_fetching_task": {
        "task": "celery_tasks.tasks.storage_health.storage_performance_schedule_fetching_task",
        "schedule": 300.0,
        "options": {"expires": 300},
    },

    # "configs_schedule_fetching_task": {
    #     "task": "celery_tasks.tasks.configs.configs_schedule_fetching_task",
    #     "schedule": 3600.0
    # },
    # "optimized_jobs_memory": {
    #     "task": "celery_tasks.tasks.jobs.optimized_jobs_memory",
    #     "schedule": 60.0,
    #     "options": {"expires": 60},
    # },
    # "slot_dynamic_adjustment": {
    #     "task": "celery_tasks.tasks.hosts.slot_dynamic_adjustment",
    #     "schedule": 60.0,
    #     "options": {"expires": 60},
    # },
    # "check_user_path_status_hourly": {
    #     "task": "celery_tasks.tasks.storages.check_user_path_status_hourly",
    #     "schedule": crontab(minute='20'),
    #     "options": {"expires": 60},
    # },
    # "synchronize_iam_user_data": {
    #     "task": "celery_tasks.tasks.iam.synchronize_iam_user_data_task",
    #     "schedule": crontab(minute='5'),
    #     "options": {"expires": 60},
    # },
    # "user_storage_usage_alert_hourly": {
    #     "task": "celery_tasks.tasks.storages.user_storage_usage_alert_hourly",
    #     "schedule": crontab(minute='0'),
    #     "options": {"expires": 60},
    # },
    # "group_storage_usage_alert_hourly": {
    #     "task": "celery_tasks.tasks.storages.group_storage_usage_alert_hourly",
    #     "schedule": crontab(minute='20'),
    #     "options": {"expires": 60},
    # },
    # "project_storage_usage_report_weekly": {
    #     "task": "celery_tasks.tasks.storages.project_storage_usage_report_weekly",
    #     "schedule": crontab(hour='14', minute='50', day_of_week='1'),
    #     "options": {"expires": 60},
    # },
    # "check_quest_db_status_hourly": {
    #     "task": "celery_tasks.tasks.check_quest_db.check_quest_db_status_hourly",
    #     "schedule": crontab(minute='30'),
    #     "options": {"expires": 60},
    # },
    # "quit_user_back_up_daily": {
    #     "task": "celery_tasks.tasks.storages.quit_user_back_up_daily",
    #     "schedule": crontab(hour='1', minute='0'),
    #     "options": {"expires": 60},
    # },
    # "synchronize_project_milestone_data_daily": {
    #     "task": "celery_tasks.tasks.iam.synchronize_project_milestone_data_daily",
    #     "schedule": crontab(hour='10', minute='30'),
    #     "options": {"expires": 60},
    # },
    # "user_large_files_alert_twice_monthly": {
    #     "task": "celery_tasks.tasks.large_files.user_large_files_alert_twice_monthly",
    #     "schedule": crontab(hour='9', minute='40', day_of_month='14,28'),
    #     "options": {"expires": 60},
    # },
    # "check_large_files_status_daily": {
    #     "task": "celery_tasks.tasks.large_files.check_large_files_status_daily",
    #     "schedule": crontab(hour='11,23', minute='30'),
    #     "options": {"expires": 60},
    # },
    # "evaluate_all_rules_parallel": {
    #     "task": "celery_tasks.tasks.lsf_alerts.evaluate_all_rules_parallel",
    #     "schedule": 60.0,
    #     "options": {"expires": 60},
    # },
}

# import celery_tasks.tasks.hosts
# import celery_tasks.tasks.jobs
# import celery_tasks.tasks.configs
import celery_tasks.tasks.storages
import celery_tasks.tasks.large_files
import celery_tasks.tasks.storage_health
# import celery_tasks.tasks.iam
# import celery_tasks.tasks.check_quest_db
# import celery_tasks.tasks.large_files
# import celery_tasks.tasks.lsf_alerts
