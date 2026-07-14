#!/bin/bash

# 设置时区和模型
export TZ='Asia/Shanghai'
export MODEL=prod

# 检查 LICENSE_ROOT_PATH 环境变量并切换到相应目录
if [ -z "$LICENSE_ROOT_PATH" ]; then
    cd /srv/prod/lsf/lsf-api
else
    cd "$LICENSE_ROOT_PATH"
fi


# 启动应用程序
uvicorn main:app --log-config logging_config.yaml --host 10.102.14.16 &
app_pid=$!

# 启动 Celery beat
celery -A celery_worker:diskpulse_app beat -l info --logfile /srv/prod/lsf/lsf-api/log/celery.beat.log &
beat_pid=$!

# 启动 Celery workers
celery -A celery_worker:diskpulse_app worker -l info --logfile /srv/prod/lsf/lsf-api/log/celery.worker1.log -n worker1%h  &
worker1_pid=$!
celery -A celery_worker:diskpulse_app worker -l info --logfile /srv/prod/lsf/lsf-api/log/celery.worker2.log -n worker2%h  &
worker2_pid=$!
celery -A celery_worker:diskpulse_app worker -l info --logfile /srv/prod/lsf/lsf-api/log/celery.worker3.log -n worker3%h  &
worker3_pid=$!
celery -A celery_worker:diskpulse_app worker -l info --logfile /srv/prod/lsf/lsf-api/log/celery.worker4.log -n worke4%h  &
worker4_pid=$!

# 定义停止所有进程的函数
stop_processes() {
    kill $app_pid
    kill $beat_pid
    kill $worker1_pid
    kill $worker2_pid
    kill $worker3_pid
    kill $worker4_pid
    exit
}

# 捕捉 SIGTERM 和 SIGINT 信号并停止进程
trap stop_processes SIGTERM SIGINT

# 等待所有进程结束
wait $app_pid
wait $beat_pid
wait $worker1_pid
wait $worker2_pid
wait $worker3_pid
wait $worker4_pid
