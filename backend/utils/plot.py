# -*- coding: utf-8 -*-
import os
import platform
from datetime import datetime
from appConfig import base_config
from typing import Any
from multiprocessing import Process
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.ticker import FuncFormatter, AutoLocator
from filelock import FileLock
import pandas as pd
import matplotlib
import logging

matplotlib.use('Agg')


def generate_plot(data: list | None, model_db: Any, message: str, image_path: str):
    if data is None:
        data = []
    if platform.system() == 'Windows':
        font_path = 'C:/Windows/Fonts/msyh.ttc'
    elif platform.system() == 'Linux':
        font_path = '/usr/share/fonts/MSYH.TTC'
    else:
        font_path = None
    # Load the font if the path is valid
    if font_path and os.path.exists(font_path):
        prop = fm.FontProperties(fname=font_path)
    else:
        prop = fm.FontProperties()

    if len(data) == 0:
        plt.figure(figsize=(10, 7))
        plt.text(0.5, 0.5, 'NO Data', fontsize=32, ha='center', va='center', color='black')
        plt.text(0.5, 0.4, '未查询到用户历史使用数据，不建议扩容', fontsize=12, ha='center', va='center', color='red',
                 fontproperties=prop)
        plt.axis('off')
        plt.savefig(image_path)
        plt.clf()
        plt.close()
        return
    dates = [str(datetime.strptime(record[0], '%Y-%m-%d %H:%M:%S').strftime('%m-%d')) for record in data]
    usage_data = [round((record[1] / 1024), 2) for record in data]  # Convert to TB

    limit = round((model_db.limit * 1.2 / 1024),
                  2) if model_db.limit else 100  # Convert limit to TB and consider a 20% buffer
    title = f' {model_db.linux_path} - Last 30 Days' if model_db.linux_path else f' {model_db.name} - Last 30 Days'

    plt.figure(figsize=(10, 7))
    plt.plot(dates, usage_data, marker='o', linestyle='-', color='#01bfec', linewidth=1)
    plt.fill_between(dates, usage_data, color='#80ffa5', alpha=0.8)
    message = f"提示：{message}" if message else "DATE"
    plt.xlabel(message, fontproperties=prop, loc='center', color='red')
    plt.ylabel('Storage Avg Usage (TB)', fontproperties=prop)
    plt.title(title, fontproperties=prop)
    plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{x:.1f} T'))
    plt.gca().set_ylim(0, limit)

    plt.axhline(y=limit * 0.8, color='red', linestyle='--', linewidth=1)
    plt.text(len(dates) - 1, limit * 0.8, 'Limit 80% horizontal line', color='red', fontsize=10,
             verticalalignment='bottom',
             horizontalalignment='right', fontproperties=prop)

    # Ensure that x-axis ticks match dates and fill the entire x-axis
    plt.xticks(ticks=range(len(dates)), labels=dates, rotation=45, fontproperties=prop)

    plt.grid(True)
    plt.tight_layout()
    plt.savefig(image_path)
    plt.clf()
    plt.close()


def plot_real_time_line(data: list, model_db: Any, role: str, message: str | None = None,
                        logger: logging.Logger | None = None):
    today_str = datetime.now().strftime("%Y%m%d")

    root_path = base_config.get('APP_ROOT_PATH') if base_config.get('APP_ROOT_PATH') else '/srv/prod/lsf/lsf-api'
    image_dir = os.path.join(root_path, 'static', 'generate_images')
    os.makedirs(image_dir, exist_ok=True)

    # Generate unique image filename
    image_id = f"{model_db.__tablename__}_{role}_{model_db.id}_{today_str}.png"
    image_path = os.path.join(image_dir, image_id)
    logger.info(image_path)
    lock_path = image_path + ".lock"

    # Use a file lock to ensure only one process can generate the image at a time
    with FileLock(lock_path):
        if os.path.exists(image_path):
            return image_path

        # Start a separate process to generate the plot
        plot_process = Process(target=generate_plot, args=(data, model_db, message, image_path))
        plot_process.start()
        plot_process.join()
    return image_path
