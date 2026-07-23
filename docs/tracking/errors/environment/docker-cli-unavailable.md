# 当前开发环境缺少 Docker CLI

## 错误内容

在 PowerShell 中执行 `docker ps` 时，系统报告无法识别 `docker` 命令，不能通过容器 CLI 检查本地或远程数据库服务。

## 解决方案

优先使用仓库虚拟环境和现有只读数据库连接进行诊断；确需管理容器时，在已安装 Docker CLI 且命令已加入 `PATH` 的环境执行，并先确认目标容器和数据范围。

## 备注

- 首次出现：2026-07-23
- 最近出现：2026-07-23
- 出现次数：1
- 出现记录：`2026-07-23-incident-evidence-time-diagnosis`；诊断事件中心未来时间时尝试执行 `docker ps`，当前 PowerShell 找不到该命令。
