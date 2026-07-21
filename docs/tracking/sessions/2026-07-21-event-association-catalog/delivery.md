# 厂商事件关联目录交付

## 范围

- 为 NetApp ONTAP EMS 和 Dell PowerScale（Isilon）事件代码建立可管理、可审核的中文关联目录。
- 让系统事件、重复故障和派生 Incident 共用同一组审核与分类边界。
- 将故障指纹回归到重复归组用途，默认展示可读事件含义，并允许打开具体日志。

## 已完成

- 新增 `vendor_event_definitions` 模型、服务、超管 API 和 Alembic revision `000000000016`；以 `(storage_type, event_code)` 唯一维护中文标题、说明、关联类型、默认等级、版本、审核状态和启停状态。
- “系统管理 → 事件关联信息”支持分页、筛选、搜索、新增、编辑、删除、启停和“同步已采集代码”；所有写操作要求超级管理员并写入统一操作审计。
- 内置 16 条官网核实的 NetApp/PowerScale 已审核定义和 7 条 PowerScale 运行时待审核候选。官网 URL 与存储类型绑定，且拒绝用户信息、端口、空白、尾点和 `@`。
- 统一“只有已启用且已审核目录影响业务”；待审核项只在超级管理员目录中保留，不形成正式中文语义、重复故障或已确认故障结论。
- 统一派生准入：已审核 `fault_log + critical` 可进入内部 `device_fault`；已审核非故障类型不得进入；未分类 `critical` 只能以“设备健康风险”保守准入并保持 `unknown`。
- 明确 `sis.auto.session.change` 是 `system_activity`，不是性能异常或故障日志；其 NOTICE 级别按项目映射保存为 `warning`。
- 将 `asset_mapping_missing` 表述为“资产映射不完整”：事件至少已归属集群，但稳定的节点/卷/Qtree/项目映射链路不完整；已有稳定节点身份的厂商事件不产生该缺口，且该缺口不表示事件代码或日志缺失。
- 重复故障和系统事件默认显示“事件代码 + 中文含义 + 关联类型”；“查看日志”打开规范化日志、对象、时间和中文说明，故障指纹仅作为可展开的技术归组键，接口不返回原始厂商载荷。
- 修复窄屏表格收缩边界；711px 视口下管理页编辑/删除和集群页“查看日志”操作均位于视口内。
- 管理 API 使用 `/storage-pulse/api/admin/vendor-event-definitions` 完整路径，部分更新使用 `PATCH`。
- Discover 是升级后一次性、幂等的历史补录和兼容修复：只对 `storage_alerts.related_info.event_code` 做数据库端 `DISTINCT`，不读取完整载荷、不在迁移中扫描，也不主动连接设备枚举代码。

## 数据库与部署边界

- 本次后端自动化验证使用 `backend/config.test.yml` 和隔离测试库；开发期间未对真实业务数据库执行迁移、Discover 或其他写入，也未修改其现有数据。
- 实际部署需在备份和变更窗口内执行迁移，再由超级管理员手工执行一次 Discover，核对新增待审核项和历史修复计数。

## 代码提交

- `88cd845 test(storage): add event association regressions`
- `0c595e1 feat(storage): add event association management UI`
- `80aad69 feat(storage): add reviewed vendor event catalog`

## 验证

- 后端目录、健康分析、Incident、证据展示、审计和迁移契约聚焦回归：198 passed。
- Alembic、后端 schema 与多方言迁移相关回归：42 passed。
- 前端目录管理、集群健康、Incident 详情、路由和 mock 回归：92 passed。
- `python -m compileall -q backend`：通过。
- 目标前端 ESLint：0 errors；保留测试夹具既有的 `vue/one-component-per-file` 18 warnings。
- `pnpm build:test`：通过；保留 `%VITE_APP_TITLE%` 未配置和既有大 chunk 警告。
- SQLite 迁移 smoke：从 revision `000000000015` 升级到 `000000000016` 后目录表与 23 条基础行存在，再降级到 `000000000015` 后目录表删除。
- 应用内浏览器 Mock 验收：超级管理员可查看和编辑全部关联目录；711px 视口下操作列可达；重复故障显示代码、中文含义和“故障日志”，点击“查看日志”可见 `secd.authsys.lookup.failed` 的规范化正文、对象、时间和中文说明。
- 文档事实搜索、CodeGraph 同步和 `git diff --check`：通过。

## 未验证范围与风险

- 真实 NetApp/PowerScale 设备事件目录、事件字段和版本差异尚需在隔离环境验收。
- 真实 PostgreSQL 迁移、Discover 计数回读、API/Celery 重启和生产登录态尚需在部署环境验证。
- 待审核代码在管理员核对官方依据前会持续显示为未分类，这是预期的安全降级。
- 浏览器控制台仍有任务外既有的 `ICarbonUserFilled` 未解析组件警告；本次页面流程没有新增业务错误。
