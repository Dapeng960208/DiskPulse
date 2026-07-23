# 后端脚本按文件路径启动时无法导入项目模块

## 错误内容

在 `backend/` 目录直接执行 `python scripts/repair_questdb_timestamps.py` 时，Python 只把 `backend/scripts/` 放入模块搜索路径，脚本导入顶层 `dependencies` 失败并报 `ModuleNotFoundError`。同一脚本作为 `scripts` 模块启动时可以正常解析项目模块。

## 解决方案

后端运维脚本使用模块入口启动：`python -m scripts.<module_name>`，并在功能文档和交付记录中提供该命令。除非项目统一建立可安装包入口，不在单个脚本中散落 `sys.path` 修改。

## 备注

- 首次出现：2026-07-23，`2026-07-23-questdb-utc-time-contract`。
- 最近出现：2026-07-23，`2026-07-23-questdb-utc-time-contract`。
- 出现次数：1。
