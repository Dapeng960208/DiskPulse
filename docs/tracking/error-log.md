# 可复现错误记录

只保留当前环境和项目结构中仍有复用价值的错误模式；已解决的逐次实施记录通过 Git 历史追溯。

| 场景 | 根因与处理 | 风险 |
| --- | --- | --- |
| 从仓库根目录运行前端 Vitest | 前端别名、测试路径和脚本均以 `frontend/` 为工作目录。进入该目录后使用 `pnpm` 脚本或 `pnpm exec vitest`。 | 错误工作目录会导致“找不到测试”或别名解析失败。 |
| 直接使用系统 `python` 或 `pytest` | 当前 PowerShell 环境没有这两个命令的全局入口。使用仓库 `.venv\\Scripts\\python.exe` 和 `backend/requirements.txt` 维护的依赖。 | 虚拟环境未初始化时，测试无法启动。 |
| 将本地自动化等同于外部集成验收 | PostgreSQL、QuestDB、Redis、Celery、LDAP、NetApp、PowerScale 和飞书不一定在本地可用。 | 外部设备权限、网络、迁移和投递结果必须在隔离部署环境确认。 |
| 前端 Mock 代替授权验证 | Mock 只模拟前端请求与展示数据。真实路由和服务端仍负责最终授权。 | Mock 成功不能证明真实账号、跨项目隔离或设备写入可用。 |
