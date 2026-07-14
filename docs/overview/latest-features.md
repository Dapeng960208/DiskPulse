# 最新功能与修复

## 2026-07-14：隐藏离职备份前端入口

- 系统管理导航不再展示“离职备份”，`/admin/backup` 路由、页面组件和后端接口保持不变。
- 系统设置不再展示目录操作和备份配置；项目组列表、编辑表单、详情以及用户目录操作不再展示备份字段和操作按钮。
- 保存其他系统设置时，已存在的备份配置仍随完整配置对象原样保留，不会被前端清空。

## 2026-07-14：存储资源按集群筛选

- Volume、聚合和 Qtree 列表筛选栏新增可清空的“存储集群”下拉框，复用现有远程搜索组件。
- 点击搜索时通过 `storage_cluster_id` 筛选对应资源；点击重置会清空集群条件并恢复全部列表。

## 2026-07-14：集群配置后自动同步卷信息

- 新建或更新启用的存储集群后，自动投递该集群的采集任务，无需等待下一次全量周期采集。
- NetApp 与 Isilon 共用现有 `StoragePulseMonitor` 链路，只采集本次配置对应的集群。
- 存储集群新增/编辑表单新增“是否启用”开关，新建默认启用，停用集群不触发采集。
- 开发环境补充 Uvicorn 可见的任务投递日志，Celery worker 补充任务开始日志。
- NetApp/Isilon 共用 `storage.tls_verify`，默认关闭证书校验以支持内部自签名设备；连接失败不再同步空数据。
- 未启用集群不触发；异步任务失败不回滚已保存配置，并由服务端日志和后续周期任务继续兜底。

## 2026-07-14：项目组标签替代项目存储环境

- 删除 `ProjectStorageEnvironment`，新增仅包含 `id`、`name` 的全局 `GroupTag`。
- `Group` 直接关联 `Project`、`StorageCluster` 和 `GroupTag`，标签只用于分类，不承载容量、采集状态或实时趋势。
- 新增 `/group-tags` 全局 CRUD 和“项目组标签”管理页；项目组表单直接选择项目、集群和标签。
- 采集、告警、用户目录、备份和周报改为从 `Group` 的直接关系解析项目、集群和标签。
- 单一 Alembic initial baseline 已改写为新模型；旧开发数据库不提供原地兼容迁移。

## 2026-07-13：清理未使用字段和无效 QuestDB 配置

- 删除 `Project`、`User`、`Host` 和 `StorageBackUpRecord` 中确认没有业务读写的 `20` 个字段，并同步收紧 API schema。
- 管理设置页和 `/config/storage` 不再暴露 `questdb_host`、`questdb_port`、`questdb_user`、`questdb_password`；QuestDB 连接统一由 `backend/config.yml` 的 `database.questdb` 配置。
- 这 `24` 个字段不进入当前单一 Alembic initial baseline；项目处于初始开发阶段，不提供旧字段回填或兼容迁移。

## 2026-06-30：后端安全默认值与敏感信息保护

- 配置和存储集群接口响应不再返回密码字段，降低前端和日志链路泄露风险。
- 后端异常响应不再回显内部异常文本，仍在服务端日志保留排障上下文。
- NetApp/Isilon 客户端默认开启 TLS 证书校验，迁移连接串和启动日志不再暴露账号密码。
- 扩容和远程文件操作加强参数校验与 shell 参数引用，降低命令注入风险。
- 列表排序、QuestDB 指标和树图字段改为白名单校验，非法字段返回稳定错误。
- 后台文件任务使用独立数据库会话，避免请求结束后继续使用已关闭 Session。
- API 鉴权收紧为 `Authorization: Bearer <token>`，登出会撤销当前 token。
- 配置和资源变更类高风险接口新增超级管理员校验，超级管理员通过 `backend/config.yml` 的 `super_admin_usernames` 配置。
- 邮件模板、任务默认值和手工集成脚本移除历史内部域名、个人邮箱和测试目录混放问题。
- 数据库连接池、Isilon 会话缓存和文档术语标准补齐为更安全的默认值。

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
