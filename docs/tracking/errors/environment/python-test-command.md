# 系统 Python 或 pytest 命令不可用

## 错误内容

在当前 PowerShell 环境直接调用系统 `python` 或 `pytest`，但全局命令入口不存在，导致测试无法启动。

## 解决方案

使用仓库虚拟环境的 `.venv\\Scripts\\python.exe`，并以 `backend/requirements.txt` 维护的依赖作为后端测试环境。

## 备注

- 分类：`environment`
- 出现次数：1
- 首次与最近出现：原平铺错误记录（原始会话日期未知）
- 出现记录：`sessions/undated-existing-records/errors.md`
