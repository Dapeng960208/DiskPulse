# 最新功能与修复

## 2026-06-30：NetApp/Isilon 软限额展示与持久化

- 新增配额链路软限额字段 `soft_limit`、`soft_use_ratio`，覆盖用户用量、Qtree/Isilon 目录、项目组和项目汇总。
- NetApp 采集 `space.soft_limit`，Isilon 采集 `thresholds.soft`，linked 用户配额继承 default-user 软限额。
- 用户用量、项目组、Qtree、Volume 列表新增软限额和软利用率展示；无软限额时显示“无软限额”。
- 存储使用导出增加“软限额”“软使用率”列；QuestDB 写入同步携带软限额指标。
- 告警口径保持现有硬利用率 `use_ratio`，不切换到软利用率。

## 2026-06-30：后端核心接口测试与导出响应修复

- 后端新增核心 API 自动化测试，覆盖认证相关路径、存储集群、项目、用户、存储层级资源、存储使用、告警、备份记录和大文件接口。
- 新增核心后端覆盖率门禁，当前 `coverage report` 结果为 `73%`，已达到初版 `70%+` 目标。
- 修复存储使用导出接口的响应类型：`export_type=pdf` 返回 `application/pdf`，`export_type=excel` 返回 Excel MIME。
- 修复大文件导出接口的响应类型，使 `.xlsx` 导出返回 Excel MIME。
- NetApp 和 Isilon 手动验证脚本改为从环境变量读取连接信息，避免代码库保留真实设备地址和凭据。
