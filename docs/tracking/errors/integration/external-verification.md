# 将本地自动化等同于外部集成验收

## 错误内容

将本地测试、Mock 或静态检查的通过结果误当作 PostgreSQL、QuestDB、Redis、Celery、LDAP、存储设备或飞书等外部依赖的集成验收结果。

## 解决方案

将本地自动化与外部集成验收分开记录；外部设备权限、网络、迁移和投递结果必须在隔离部署环境确认。

## 备注

- 分类：`integration`
- 出现次数：1
- 首次与最近出现：原平铺错误记录（原始会话日期未知）
- 出现记录：`sessions/undated-existing-records/errors.md`
