# 当前交付记录

## 2026-07-17：侧栏导航顺序与图标优化

- 可见一级入口采用一致的 Remix Icon；系统管理可见子项按存储资源、组织与用户、平台设置、AI 中心的常见运维管理顺序展示。
- 路由、角色权限、隐藏离职备份与详情入口均未修改。路由菜单与动态组件加载聚焦测试为 `2 files / 6 passed`，目标 ESLint、生产构建与 `git diff --check` 通过；构建保留既有大 chunk 警告。
- 完整设计见 [导航顺序与图标优化设计](../superpowers/specs/2026-07-17-navigation-order-and-icons-design.md)。

## 2026-07-17：应用壳内置 Q 版动态默认头像

- 顶部用户菜单在 `avatarUrl` 为空时显示四个原创内置 Q 版 GIF 之一；通过稳定哈希按用户名或展示名称选择，避免刷新时随机切换；后端已有头像仍保持最高优先级。
- 新增 4 个 96×96、两帧 GIF 静态资源和默认头像选择工具，不新增后端接口、数据库字段或权限；单元测试为 `2 passed`，目标 ESLint 与 `git diff --check` 通过。
- 已检查 GIF 尺寸、帧数与首帧视觉效果；未执行真实登录态的浏览器验收，因此 LDAP profile 非空头像在本轮未做端到端确认。完整边界见 [应用壳内置默认头像](../features/app-shell/default-avatars.md)。

## 2026-07-17：全站内容区统一外层间距

- 根因是 `AppLayout`、共享页面样式和页面根节点重复声明外层 padding，同时 Element Plus `ElMain` 默认 `20px` 未显式清零，导致不同页面上下左右留白不一致。
- 实现由 `AppLayout` 成为唯一 gutter 所有者：桌面四边 `16px`，`<=768px` 为 `12px`；面包屑同步对齐；页面内部 QueryForm、DataTable、卡片、表单、页签和图表间距保持不变。
- TDD RED 为 `11 tests | 9 failed, 2 passed`，GREEN 为 `11/11`。目标 Vue 文件与合同 ESLint 通过；覆盖率 `61 files / 370 tests passed`，Statements `98.3%`、Branches `88.74%`、Functions `84.17%`、Lines `98.3%`；`build:prod` 成功但保留既有大 chunk 警告，`git diff --check` 通过。
- 浏览器验证覆盖 13 个可加载在用路由于 `1383x994`、`936x994`，以及 `/usage` 于 `375/414/768`；确认桌面 `16px`、移动 `12px` gutter、面包屑对齐与 `ElMain` 无外层 padding。旧依赖预构建缓存刷新后，`/ai/chat` 在当前桌面额外验证通过：`.ai-workspace` 存在、gutter 为 `16px`、无 Vite overlay，整页刷新后 console errors 为 `0`。22 条路由静态矩阵覆盖详情页结构。
- 风险：真实 ID 详情页未浏览器验证；`320px` viewport override 未生效；`375/414` 既有固定侧栏水平溢出未由本轮引入或扩展修复。
- 完整设计与验收边界见 [应用内容区统一间距设计](../features/app-shell/content-spacing.md)。

## 2026-07-17：实时监控页删除重复时间并展示告警紧急程度

- 页头不再重复显示当前开始、结束时间，时间范围筛选器和查询参数保持不变。
- 告警表删除 `description` 对应的“提示”列，新增“告警紧急程度”列；重要、严重、紧急及历史高/中等级使用中文标签和对应告警色，触发值、时间继续展示。
- TDD RED 提交为 `40a5dc1`，GREEN 提交为 `73a330c`。实时监控、告警规则、详情路由和页面烟测组合验证为 `4 files / 25 passed`；生产代码 ESLint `0 errors`，测试文件仅保留 18 条既有单文件多组件 warning，生产构建通过并保留既有大 chunk 提示。
- 按用户此前要求未执行浏览器自动化验证；完整设计见 [实时监控页头与告警紧急程度展示设计](../features/storage-trends/realtime-header-alert-level.md)。

## 2026-07-17：用户目录详情暂时隐藏第 2–4 行字段

- `UsageDetailPage.vue` 已用 Vue 模板注释保留文件数量、目录权限、访问/修改/改变时间、创建时间、权限组、Inode、硬链接、IO 块和设备标识等 12 个扩展字段，页面暂时只展示第一行摘要。
- `ElDescriptionsItem` 导入同步保留为代码注释；共享实时趋势、接口、数据和告警逻辑不变。
- TDD RED 提交为 `8e604f4`，GREEN 提交为 `c23026f`。用户目录详情、页面烟测和路由依赖组合验证为 `4 files / 17 passed`，目标 ESLint、生产构建通过；按用户要求未执行浏览器验证。
- 设计与恢复方式见 [用户目录详情扩展字段隐藏设计](../features/storage-trends/usage-detail-field-visibility.md)。

## 2026-07-17：修复项目组与用户目录详情动态加载

- 在当前 `localhost:5173` 新浏览器会话中复现：`element-plus_es_components_row_style_css.js` 和 `...col_style_css.js` 返回 `504 Outdated Optimize Dep`，随后 Vue Router 报 `GroupDetailPage.vue` / `UsageDetailPage.vue` 动态导入失败。
- 删除两个详情页及共享 `RealTimePage` 中未使用的 `ElRow`、`ElCol`，保留描述字段、实时趋势、接口和路由不变；没有增加自动重试或修改 Vite 依赖优化配置。
- TDD RED 提交为 `d9b1d2f`、`007ffc3`，GREEN 提交为 `ed54e81`。聚焦测试 `3 files / 14 passed`，目标 ESLint 和生产构建通过；浏览器复验两个路由均不再出现 `504` 或动态导入失败。
- 浏览器使用无登录令牌的新会话，因此业务 API 返回 `401`，没有验证真实详情数据；当前已经打开的旧标签页需刷新一次以丢弃失败的模块请求。

## 2026-07-17：全站存储趋势图重设计

- 新增共享 `StorageTrendChart` 和统一 option 构建器，替换实时趋势、Dashboard 容量趋势和存储集群容量分析中的旧存储趋势组件；旧 `LineCharts`、`MultipleLineCharts` 已退出生产使用。
- 单对象曲线按有效规则分为蓝 `#446AEE`、金黄 `#D69B1E`、橙 `#EF5923`、红 `#D3372F` 四段，阈值交点通过插值准确换色；百分比纵轴固定 `0–100%`、水平网格使用虚点线，三级标签位于对应阈值线上方。
- 实时趋势新增 `indicator=alert_ratio`；`trend_meta` 明确硬/软口径、系统/项目/项目组规则来源、三级阈值、容量限额和实际历史使用率列。现有 `used`、`use_ratio`、`file_used` 保持兼容，非法指标返回 `422`。
- Dashboard 全局趋势和存储集群物理容量固定采用系统规则与硬容量；项目 Dashboard 使用项目有效规则；多对象容量不显示阈值，多对象使用率按系统阈值对比。
- QuestDB 复用现有 `000000000002_add_soft_quota_metrics.sql`、模型和采集写入中的可空 `soft_limit`、`soft_use_ratio`，未新增迁移；迁移前历史为空时保留数据缺口。
- TDD RED 提交为 `5d38a7a`，GREEN 提交为 `e3083f6`。最终后端全量 `392 passed`；前端全量 `58 files / 351 passed`，Statements/Lines `98.29%`、Branches `88.60%`、Functions `84.13%`，lint、生产构建、Python `compileall` 和 `git diff --check` 通过。构建仅保留既有大 chunk 提示，前端测试仅保留既有负向网络日志。
- Mock API 浏览器验收覆盖 `1440×900` 和 `390×844`、亮色/暗色、Tooltip 与三级阈值：桌面无横向溢出，移动端折叠导航后阈值标签完整且趋势图自身未越界；既有顶部用户操作区在 `390px` 仍造成约 `39px` 应用壳横向溢出，本轮未扩展为全局头部重构。
- 浏览器验收曾发现单对象固定线色覆盖 `visualMap`，按 TDD 增加失败断言后修复并复验为真实四色分段；记录见 [错误日志](./error-log.md)。真实 PostgreSQL、QuestDB 历史和登录态 API 尚未验证。
- 完整设计与接口口径见 [全站存储趋势图设计](../features/storage-trends/design.md)。

## 2026-07-17：Dashboard 图表化总览

- Dashboard 已拆分为 `/summary`、`/capacity-trend`、`/capacity-items`、`/alert-levels` 和项目必选的 `/top-users`，旧 `/overview` 与 `/alert-trend` 返回 `404`。
- 全局按启用存储集群汇总物理容量，项目按配额与启用监控项目组汇总；用户排行通过用户目录关联项目组，按用户汇总已用容量后取前 10。
- 项目切换改为摘要和图表分区加载，画布使用顶部对齐的固定内容轨道，修复整体骨架期间的大面积纵向留白；任一接口失败只影响对应面板。
- 项目视图新增“用户使用 Top 10”横向排行图；项目组容量、用户排行和告警级别按 `2:2:1` 同排，`1024px` 及以下改为单列。
- 告警改为按 `alert_level` 汇总的饼图，固定优先展示重要、严重、紧急，继续排除配额调整和厂商事件。
- 修复全局容量趋势将数值集群 ID 直接插入 QuestDB `SYMBOL` 查询导致空数组的问题；改为绑定字符串 ID 后，真实 QuestDB 返回 `2026-07-14` 至 `2026-07-17` 共 4 个日采样点。
- 项目容量趋势仍无数据：真实 `project_storage_usages` 记录数为 0，现有采集器没有写入项目级时序指标，属于采集链缺口，不是 Dashboard 接口过滤问题。
- 本轮追加 TDD 检查点：布局设计 `b21635a`、告警设计 `f0b1a79`、RED `047d8da`、GREEN `10101b1`。后端聚焦测试 `5 passed`，前端 Dashboard/API/图表组合测试 `15 passed`。
- 目标 ESLint 为 `0 errors`（测试桩保留 5 条既有单文件多组件 warning），生产构建和 Python `compileall` 通过；构建保留既有大 chunk warning。
- 已连接当前配置的 PostgreSQL 与 QuestDB 验证全局趋势和告警级别；未使用真实登录态浏览器复验页面像素布局，项目趋势需补齐采集写入后再验收。

## 2026-07-17：前后端覆盖率门禁与 CI 基线调整

- 覆盖率规范调整为后端全局门禁 `85%`、前端四项指标门禁 `80%`；代码、项目规范和 GitHub Actions 统一使用该口径。
- GitHub Actions 固定 Node `22.14.0` 与 Python `3.13.0`，执行后端全量测试/coverage、前端全量 coverage、lint 和生产构建。
- 本轮验证：后端 `363 passed`、coverage `91%`；前端 `294 passed`，Statements/Lines `98.40%`、Branches `89.84%`、Functions `83.95%`，在新门禁下通过；前端 lint 和生产构建通过。
- 后端重复 warning 已从全量测试输出中清除；前端仅保留负向网络用例产生的预期错误日志和构建既有大 chunk 提示。GitHub-hosted runner 尚未实际执行，需以远端 Actions 结果为最终环境验证。
## 2026-07-16：全局列表使用率与响应式列优化

- 新增登录用户可读的 `GET /config/storage-alert-thresholds`，只返回 `important/serious/emergency`；完整 `/config/storage` 读写继续要求超级管理员。
- 七个列表页统一使用率列 `240px`、操作列 `132px`，并按 `1440px`、`1024px` 两个断点实时隐藏次要列和容量上下文列；窄屏始终保留主标识、使用率和操作入口。
- `Progress` 通过 Pinia 共享一次阈值请求，失败静默回退默认 `80/90/95`；设置保存后立即更新缓存。颜色规则为绿 `<80`、橙 `80–<90`、红 `90–95`、深红 `>95`，实际边界跟随配置阈值。
- TDD RED 提交为 `6f0025b`；聚焦验证为后端 `51 passed`、前端 `51 passed`，新增 Pinia 烟测复验 `68 passed`；后端全量 `340 passed`，前端排除两份已失效基线契约后的覆盖率回归为 `257 passed`，Statements/Lines `92.69%`、Branches `83.26%`、Functions `68.19%`。
- `npm run lint`、`npm run build:prod` 和 `git diff --check` 通过。完整 `npm test` 与 `npm run test:coverage` 均为 `272 passed, 3 failed`；三个失败在主工作区同一基线上可复现，来自已移除的 LDAP 新增/同步按钮和用户目录移动入口旧断言，与本轮改动无关。
- 三档列映射已由 `1600/1200/900px` 自动化契约覆盖；未连接带登录态的本轮 Worktree 前端与后端执行浏览器人工验收，长文本 tooltip、真实视口切换和设置保存后的页面即时变色仍需部署环境确认。


## 2026-07-16：项目组与用户目录配额调整

- NetApp/Isilon 所有设备 HTTP 调用统一保留厂商错误响应：登录、探测、读取、写入、异步任务查询、写后读回和注销均记录原始状态码与消息，不再吞成 `False` 或空结果；同步配额接口原样返回状态码、响应体和 `Content-Type`，JSON 与纯文本均不包装。只有设备无 HTTP 响应的连接、DNS、TLS、超时等错误才返回 `502`。
- 本轮 TDD 覆盖 NetApp 原生 `403`、Isilon 登录/探测/缓存 Session 验证原生错误，以及配额 JSON/纯文本响应透传；相关存储客户端、配额、Session、资源映射和健康分析测试共 `159 passed`，目标模块 `compileall` 通过。
- 配额调用在集群显式配置 `tls_verify=false` 时不再重复输出 `InsecureRequestWarning`。
- 存储集群表单内置的 root 授权命令及存储集群文档已统一修正：监控权限只读，`ISI_PRIV_QUOTA` 父权限和 `ISI_PRIV_QUOTA_QUOTAMANAGEMENT` 子权限均为写权限；既有只读角色先删除 `ISI_PRIV_QUOTA:r` 再按父子顺序重建写权限。
- 修复 Isilon 已有 Directory quota 更新 payload：PUT 仅提交 OneFS 允许修改的 `thresholds`，不再携带只用于创建的 `type/path`。TDD RED `fb3d0af`、GREEN `e4b6453`，聚焦测试 `9 passed`。真实设备等值 PUT 返回 `403 AEC_FORBIDDEN`；OneFS 要求父权限不能低于子权限，因此 `ISI_PRIV_QUOTA` 与 `ISI_PRIV_QUOTA_QUOTAMANAGEMENT` 必须同时配置为写权限。
- 配额弹窗已复用全局 `write-form` 标题、分组、顶部标签、紧凑宽度和底部操作区；软限额单位由灰色静态文本改为可选下拉，切换 GiB/TiB 时同步换算硬、软限额数值。
- 修复前端权限角色不一致：后端 profile 返回的 `superadmin` 现在被前端识别为全局角色，超级管理员可看到项目组和用户目录的“调整配额”入口。
- 项目组和用户目录操作列统一为固定宽度的“详情 + 更多”：普通用户只显示详情，管理员菜单按页面现有能力提供调整配额、编辑和删除；添加项目组与新增用户目录也统一仅管理员可见。
- 操作列样式按 TDD 完成：RED `23fd3ce` 为 `5 failed, 1 passed`，GREEN 聚焦测试为 `6 passed`；定向 ESLint 和 `npm run build:test` 通过，构建仅保留既有大 chunk 警告。未使用真实普通用户与超级管理员账号执行登录浏览器验收。
- 全站表格行操作规则已扩展到存储集群和 AI 模型：超过两个操作时只保留一个高频操作与“更多”，共享样式移入全局 `style.scss`；筛选栏、表头、工具栏、卡片和弹窗操作不受影响。
- 存储集群保留“详情”，管理员菜单提供编辑和删除，新增入口只对管理员显示；AI 模型保留“编辑”，连接测试和删除进入更多菜单，删除继续通过 `ElMessageBox` 二次确认。
- 全局契约测试递归扫描 Vue 表格行操作。RED `52653ae` 为 `3 failed, 6 passed`，只命中存储集群和 AI 模型；GREEN `19b7cf2` 为 `9 passed`。定向 ESLint 和 `npm run build:test` 通过，构建仅保留既有大 chunk 警告。真实普通用户与超级管理员登录态浏览器验收未执行。
- 已新增 `PATCH /groups/{id}/quota` 和 `PATCH /storage-usages/{id}/quota`，仅超级管理员可调用；请求禁止额外字段，硬限额必填，软限额可选且必须严格小于硬限额。
- 统一 quota service 根据集群类型调用现有 NetApp/Isilon 客户端：NetApp 支持 Qtree/用户 quota rule 和 Volume 容量，Isilon 支持 Directory/User quota 与宽限期；linked default-user 会创建显式用户配额。
- 设备写入后执行读回校验，再同步本地资源、写 `quota_adjustment` 记录并在数据库提交后发送邮件；共享目标返回 `409`，设备 HTTP 错误保留原始响应，无设备响应或读回失败返回 `502`。
- 项目组和用户目录列表复用统一弹窗；NetApp Volume 项目组隐藏软限额，宽限期仅 Isilon 显示，新硬限额低于已用容量时要求二次确认。
- TDD 检查点：后端 RED `8c7629a`/`e00d38c`、GREEN `d5c1eef`；前端 RED `44418fd`、GREEN `41221d9`。验证为后端 `8 passed`、前端聚焦 `4 passed`、页面烟测 `64 passed`，`compileall`、定向 ESLint 与 `npm run build:test` 通过。
- 未连接真实 NetApp/Isilon 测试目标执行写入、读回和恢复原值；未运行后端全量回归。完整边界见 [配额调整设计](../features/storage-quota/quota-adjustment-design.md)。

## 2026-07-16：系统设置废弃配置清理

- 系统设置已收敛为普通“系统设置”标题、存储告警规则和保存按钮；邮箱配置与邮件链接仅从页面隐藏，`mail_*`、`company`、`domain_name`、`person_expand`、`group_expand` 及邮件发送逻辑继续保留。
- `storage_conf`、ORM 和配置 schema 已删除 IAM、BPM 与全局存储连接九个字段；`000000000007_deprecated_config_cleanup` 升级物理删列，降级恢复 `nullable` 空列。`storage_clusters` 中每集群连接凭据、当前容量/事件/性能/告警采集和其他备份逻辑不受影响。
- 已删除 IAM/BPM 集成、旧 `/storage-usages/expand`、`StorageManagement`、`SynchronousPathState`、`LargeFileState` 及对应未启用任务；大文件邮件告警仍保留。生产引用与敏感日志扫描无残留。
- TDD RED 提交为 `2e36631`；前端相关测试 `10 passed` 且目标 ESLint 通过，后端聚焦测试 `84 passed`，独立只读验收后端全量 `326 passed`。`compileall`、Alembic `heads`/`history` 通过，唯一 head 为 `000000000007`。
- SQLite 在线升降级及 SQLite/PostgreSQL/MySQL 离线 SQL 生成通过；未连接真实 PostgreSQL/MySQL 执行迁移，部署前需在目标数据库完成备份、升级和回滚验证。完整边界见 [系统设置废弃配置清理设计](../features/system-settings-cleanup/design.md)。

## 2026-07-16：写入表单体验重构

- 已统一存储集群、用户、项目、项目组、项目组标签、用户目录、AI 模型和系统设置的写入体验：弹窗采用普通标题、顶部标签、语义分组、响应式单/双列网格和具体动作按钮；标题区不再显示蓝色背景和副标题，系统设置采用页面内分组与固定保存区。
- `useForm` 新增模型快照与脏状态、重复提交保护、异步提交、成功后快照重置，以及校验失败时滚动并聚焦首个无效字段；`useDialog` 新增提交中关闭保护、未保存关闭确认和成功后的强制关闭。
- 删除存储集群、用户、项目组、项目组标签，备份删除/回滚和用户目录移动的确认框已明确操作对象、不可撤销影响与具体确认动词；LDAP 同步继续说明状态变更边界。
- TDD 检查点：生命周期 RED `0dafe5a`、GREEN `7ddf21c`；页面体验 RED `842c035`、GREEN `fcf919e`。受影响回归为 `7 files / 51 passed`，前端全量为 `41 files / 223 passed`；覆盖率 Statements/Lines `92.82%`、Branches `82.25%`、Functions `69.43%`。
- `npm run lint`、`npm run build:prod` 和 `git diff --check` 通过；构建仅保留既有大 chunk 提示，测试仅保留既有 Sass 弃用、`v-loading` mock 和 jsdom CORS 日志。
- 本地浏览器在 `1280×720` 验证紧凑表单为 `480px`；`414×896` 下弹窗宽 `382.4px`，页面与弹窗横向溢出均为 `0`。修改字段后关闭会出现“继续编辑 / 放弃修改”确认。
- 普通标题区调整的 TDD RED 为 `012443b`（`1 failed, 11 passed`），GREEN 为 `f1b3ddc`（`12 passed`）；`npm run build:prod` 和 `git diff --check` 通过，生产代码仅修改共享 `write-form.scss`。
- 浏览器验收未连接后端和登录态，列表请求显示网络错误，未提交真实创建或修改；真实 API 成功/失败反馈、权限差异和复杂双列表单仍需部署环境验收。字段语义、payload、API、权限和后端流程未修改。完整边界见 [写入表单体验重构设计](../features/form-experience/design.md)。

## 2026-07-16：筛选栏密度与时间范围适配

- `QueryForm` 展开高级筛选时改为与主筛选连续流入同一个 `1–5` 列网格；操作按钮保持独立右侧轨道，普通关键词仍占一个标准列。
- 秒级 `datetimerange` 使用 `.query-form-field--date-range` 跨两个标准列，手机端回落单列；移除存储健康页原有的局部 `480px` 宽度补丁。
- TDD RED 提交为 `ca2fd35`（聚焦测试 `3 failed, 1 passed`），GREEN 聚焦测试为 `4 passed`。前端全量 `40 files / 207 passed`，覆盖率 Statements/Lines `92.73%`、Branches `81.85%`、Functions `70.92%`，其中 `QueryForm.vue` 为 `100%`；lint 和生产构建通过，构建仅保留既有大 chunk 提示。浏览器在 `1920px` 验证项目组展开后首行 5 个等宽组件（每项约 `242.9px`），时间范围宽约 `553.8px` 且两个 `YYYY-MM-DD HH:mm:ss` 完整显示；`1024px` 自动为两列，`414px` 无页面横向溢出。

## 2026-07-16：存储告警规则与飞书通知

- 告警记录新增“集群”列；列表接口按当前资源关系批量补全 `cluster_name` 和 `project_name`，历史用户目录告警即使上下文未保存项目也可正确显示。TDD RED 为 `74c9780`，GREEN 为 `c936de3`；后端聚焦 `30 passed`、前端聚焦 `8 passed`，目标 lint 与 `npm run build:test` 通过。
- 已从本地 `main` HEAD `ffe5d15` 创建独立分支 `codex/storage-alert-rules` 和 Worktree `D:\dev\worktrees\DiskPulse\storage-alert-rules`；主工作区 `frontend/src/pages/usage/UsageListPage.vue` 的既有修改未复制、未回退、未暂存。
- 已复制 `.codegraph`，仅清理目标副本中的 daemon/WAL 运行文件并完整重建索引；`codegraph status` 显示新 Worktree 路径、286 个文件、3,866 个节点、9,936 条边和 `[OK] Index is up to date`。
- `npm ci` 成功；Alembic 唯一 head 为 `000000000005`，history 连续。
- 初始后端全量基线为 `283 passed, 1 failed`，失败是迁移测试错误选择最后一个迁移；初始前端全量基线为 `194 passed, 2 failed`，失败是存储术语旧断言。两类问题已由独立提交 `d16e8f1` 修复，复验为后端 `284 passed`、前端 39 个测试文件共 `196 passed`，实施基线已恢复。
- 已完成系统、项目、项目组完整规则与继承：硬/软口径、严格递增阈值、正整数重复频次、连续两次确认、升级、静默降级、同级重复、恢复和规则变化静默重置均已实现。
- `000000000006_storage_alert_rules` 已新增规则字段、项目默认告警开关、项目组个人 CC、`storage_alert_states` 和告警 outbox 投递字段/索引；历史告警回填为 `trigger/hard/legacy`。
- `backend/celery_worker.py` 已独立注册每分钟 `storage_alerts_schedule_task`；该任务读取最新已提交采集批次后评估，容量采集任务不再投递告警。状态与事件同事务提交，飞书 HTTP 由 `deliver_storage_alert_task` 处理，每分钟补偿任务按 1/5/15 分钟重试。旧容量邮件代码保留但 Beat 调度继续关闭。
- 独立调度调整按 TDD 完成：RED 提交 `b12b73b`，聚焦测试 `29 passed`，后端全量 `314 passed`，仓库覆盖率 `87%`；静态加载确认任务已注册且 Beat 周期为 60 秒。
- 飞书配置默认关闭，协议使用 `/auth/token`、Bearer Token 和 `/send_info` 富文本 `post`；业务收件人、全局 CC、项目组 CC、紧急管理员和 debug 替换均已实现，密钥、收件人快照和内部错误不进入公开 API。
- 部署实例已确认告警评估和重试正常生成事件，但飞书地址解析到 `10.0.42.47` 后 TCP `32013` 不可达，最新事件 4 次发送均超时；连接恢复前不会收到提醒。已修复新消息与历史列表的中文摘要、事件、限额口径和三级告警标签，并为用户目录补充项目上下文；失败历史事件不自动重放。
- 后台已提供系统规则页签、项目告警/自定义规则、项目组继承预览/个人 CC，以及告警事件类型、限额口径和发送状态筛选；共享 `StorageAlertRuleForm` 负责三处规则校验。
- TDD RED 契约提交为 `84b0d47`。最终后端全量 `312 passed`，仓库 coverage `84%`（通过现有 80% 门禁，但未达到本计划 90%），规则 schema/服务/飞书核心选择性覆盖率 `92%`；前端 40 个测试文件、`205 passed`，Statements/Lines `92.62%`、Branches `81.96%`、Functions `70.29%`，lint 和生产构建通过。
- Alembic 唯一 head 为 `000000000006`；SQLite 在线升降级、SQLite 离线 SQL 实际执行、PostgreSQL/MySQL 离线 SQL 生成通过。`compileall`、`pip check`、`git diff --check` 与最终 CodeGraph 同步/status 通过。
- 未验证真实 Redis/Celery、飞书通知微服务、PostgreSQL/MySQL 在线迁移、真实多集群部分失败和登录浏览器人工验收；覆盖率差距与部署验收边界保留为交付风险。完整实现与验收证据见 [存储告警规则设计](../features/storage-alerts/design.md)。

## 2026-07-16：Isilon 性能按 Directory Quota 路径采集

- 原采集错误选择 node 磁盘 latency，导致性能页显示 `node 1 / 0ms`；现改读 OneFS `path` performance dataset、workload 配置和 dataset statkey。
- workload ID 映射为完整路径，读/写/其他累计延迟按请求数求加权平均并从微秒转为毫秒，QuestDB 对象类型统一为 `volume`；前端只查询 Volume，历史 node 数据不再进入页面 Top 10。
- TDD RED 提交 `7dfc158` 为 `3 failed`；GREEN 存储健康后端 `93 passed, 1 deselected`，前端页面 `10 passed`，目标前端 lint `0 errors`。真实 OneFS 9.11.0.5 的 8 个已固定 workload 中有 7 个匹配 Directory Quota；正式采集写入并通过服务接口回读 7 个路径，额外父路径不会再误标为存储空间。
- 外部配置边界：数据库有 67 个 Directory Quota，设备 `path` dataset 当前仅有 7 个匹配 workload。要覆盖其余 60 个路径，root 需逐个执行 `isi performance workloads pin path "path:<完整路径>"`，固定后等待至少 30 秒；`ISI_PRIV_PERFORMANCE` 只提供读取权限，不会自动固定 workload。
- 首次验证写入的一条非 Directory Quota 父路径样本因 QuestDB 不支持该表行级 `DELETE` 而保留到 TTL 到期；服务端按 PostgreSQL Volume 名称过滤，页面和导出均不会返回该样本。

## 2026-07-16：系统事件搜索、分页与对象语义

- `system-events` 接口新增 `keyword`、`severity`、`page`、`page_size`，默认每页 20 条、最多 100 条；数据库先按集群、时间、关键字和等级过滤，再执行 `count` 与分页。
- 前端在系统事件区复用全局 `QueryForm`，增加关键字和日志等级筛选，保留故障页共用时间范围；翻页和每页条数变化只刷新系统事件，不重复刷新严重级别图和重复故障表。
- 事件对象同时返回 `object_id`、`object_name`、`object_type`：NetApp 历史数据从原始 EMS `node.name` 优先生成名称，Isilon `devid` 格式化为“节点 N”，原始标识继续用于厂商侧核对。
- TDD RED 提交为 `cdce770`；GREEN 为后端存储健康 `90 passed, 1 deselected`、前端 `10 passed`。页面聚焦覆盖率为 Statements/Lines `93.98%`、Branches `72.52%`；后端分析 Service 模块为 `82%`。完整存储健康测试仍有一个既有迁移顺序用例失败，见 `docs/tracking/error-log.md`。
- 未执行登录浏览器和真实 PostgreSQL/MySQL API 冒烟；关键字对 JSON 原始事件的匹配已在 SQLite 聚焦测试覆盖，生产数据库查询计划仍需部署后观察。

## 2026-07-16：恢复 Isilon 性能与设备事件解析

- 真机确认 Isilon 认证和接口均正常：statistics 返回 `1` 条节点磁盘延迟，event group/list 返回 `2888`/`218` 条；此前空页面由应用解析兼容问题导致，不再属于账号或权限阻塞。
- 延迟采集支持 OneFS 返回的 `seconds` 并转换为毫秒，保留 `0.0` 合法样本；statistics 的 `time` Unix 时间戳作为指标采集时间。
- OneFS event list 的嵌套 `events[]` 现会展开，event group 使用 `last_event/time_noticed`、`causes` 和 `specifier.devid` 生成事件时间、代码、描述和对象标识。
- TDD RED 检查点为 `eea05df`（`4 failed, 9 passed`）；GREEN 相关解析测试 `24 passed`，目标任务模块分支覆盖率 `83%`。真实 OneFS 无写入复验得到性能 `1/1` 条、事件 `3888` 条，其中最近 8 小时 `94` 条、最近 24 小时 `331` 条。
- 测试环境已执行正式采集并写入 QuestDB 性能 `1` 条、PostgreSQL 事件 `331` 条；随后重启 worker 与 Beat，异步性能任务被消费后 QuestDB 记录增至 `2` 条，最新时间为 `2026-07-16 10:39:54`。页面刷新后可直接查询这些数据。
- Windows `solo` worker 在 OneFS 长分页期间可能不响应 inspect；本轮以进程存活、任务投递和数据库时间戳更新共同确认持续采集已加载新代码。

## 2026-07-15：全站渐进式筛选栏改造

- 共享 `QueryForm` 已改为紧凑工具栏：筛选项统一为左对齐 label 与等宽控件，主筛选和高级筛选按容器宽度自适应为每行 `1–5` 项；支持高级条件数量、条件标签和动作插槽。操作顺序统一为“更多筛选、重置、绿色导出、蓝色搜索”，搜索固定在最右侧。
- 项目组常驻“项目组名、关联项目、存储集群”，用户目录常驻“研发用户名、项目、存储集群”；其余条件进入“更多筛选”。删除标签和重置会清除依赖参数、重置页码并立即查询，未改变后端接口或普通搜索触发方式。
- TDD RED 检查点为 `da322f2`；GREEN 聚焦测试 `15 passed`。`npm run lint`、`npm run build:prod` 通过；完整前端回归 `190 passed, 2 failed`，仅保留已记录的两条存储术语旧断言失败。
- 排除上述已知失败文件后的覆盖率验证为 `188 passed`：Statements `92.58%`、Branches `81.80%`、Functions `72.04%`、Lines `92.58%`，其中 `QueryForm.vue` 四项均为 `100%`。覆盖率插桩下的既有重型组件测试统一使用 `30s` 超时。
- 浏览器已验证项目组和用户目录在亮色/暗色主题下的主/高级布局、按钮顺序和配色；`414/768/1024/1440/1920px` 无横向溢出。既有固定应用壳在 `320/375px` 仍会溢出，本轮未扩大为全局导航重构；未使用真实筛选数据验证标签删除后的后端查询结果。
- 等宽网格补充 RED 检查点为 `7956371`、`2ff7a1c`、`007b4d2`；聚焦测试 `3 passed`。浏览器确认 `1920px` 最多 5 列、`1024px` 2 列、`414px` 1 列，三档筛选栏内部溢出均为 `0`；桌面 label 为左对齐、`14px/600` 字重。
- 上下行共享字段轨道的 RED 检查点为 `3dce493`，同一聚焦测试 GREEN 为 `3 passed`，全前端 lint 和生产构建通过；用户目录含导出按钮时，浏览器在 `1920px` 确认主筛选和高级筛选均为 5 列、字段宽度均为 `226.2px`，按钮轨道为 `350.8px`，筛选栏溢出为 `0`，且未增加隐藏占位节点。

## 2026-07-15：登录页存储集群主题改版

- 登录页采用 Split Studio 左右分屏：左侧展示生成的存储服务器集群背景、品牌与容量/性能/故障能力，右侧保留 LDAP 用户名和密码登录。
- 认证调用、JWT 保存、profile 获取和登录后跳转逻辑未修改；新增视觉契约测试锁定分屏结构、主题文案和背景图替代文本。
- TDD RED：聚焦测试 `1 failed, 1 passed`；GREEN：同一测试文件 `2 passed`。目标 Vue 文件 ESLint 和 `npm run build:prod` 通过，构建保留既有大 chunk warning。
- Playwright 已验证亮色/暗色桌面布局，并在 `320px`、`375px`、`414px`、`768px` 下确认 `scrollWidth` 等于视口宽度，无横向溢出。
- 未连接真实 LDAP 账号执行登录；认证链路由现有 mock 测试覆盖，本轮浏览器验证仅覆盖页面显示、主题切换和响应式布局。

## 2026-07-15：存储类型与软限额标签样式统一

- 新增全局 `.storage-info-tag`，统一 6 个前端文件中的 12 个存储类型和“无软限额”标签落点；页面不再维护私有标签颜色。
- 后端 `storage_type`、`soft_limit`、`soft_use_ratio` 模型、schema、CRUD 和导出字段保持一致，本轮无需修改接口。
- TDD RED：聚焦测试 `1 failed`；GREEN：同一聚焦测试 `1 passed`。
- 定向 ESLint、生产构建通过；后端软限额契约测试 `4 passed`。
- 扩展前端组合测试为 `9 passed, 2 failed`：失败来自当前工作区已删除的用户目录“存储目标”列，以及已移除协议/TLS 摘要但仍保留旧断言的存储集群详情测试，均未在本轮回退。
- 未执行登录态浏览器截图验证；明暗主题继续共用既有紫色 token。

## 2026-07-15：存储一览并入存储集群详情

- 删除系统管理中的独立“存储一览”路由和页面，在存储集群详情“容量趋势”旁新增“存储分布”页签。
- 存储分布复用既有 `fetchAggregateTrees` 接口，按详情页当前 `clusterId` 首次打开时懒加载，普通页签往返不重复请求；该页签隐藏无关的时间筛选和报告导出工具栏。
- TDD RED：聚焦测试 `3 failed, 7 passed`；GREEN：详情页和路由聚焦测试 `11 passed`，targeted ESLint `0 errors`（保留测试文件既有 `vue/one-component-per-file` warning）。
- 未执行登录浏览器、真实后端接口或全量前端回归；容量树接口和图表沿用既有实现，本轮未修改后端。

## 2026-07-15：认证 token 接入 Redis 会话缓存

- JWT 默认有效期从 60 分钟调整为 `10080` 分钟（7 天），Redis token key 使用相同 TTL。
- 登录写入 `diskpulse:auth:token:<jti>`，value 为 JWT SHA-256 摘要；鉴权要求签名、到期时间和 Redis 白名单同时有效，登出删除对应 key。
- Redis 连接失败时登录/鉴权 fail-closed 返回 `503`；当前配置的 Redis DB 7 已通过 `PING` 检查。
- TDD RED：`4 failed, 6 passed`；GREEN：同一聚焦认证测试 `10 passed`，认证/安全/核心接口组合测试 `53 passed`，后端全量 `262 passed`。
- `backend/utils/security.py` 分支覆盖率 `84%`；`compileall`、`pip check` 通过。真实 Redis 临时 token TTL 为 `604800` 秒，删除会话后同一 token 返回 `401`。
- 本地 `backend/config.yml` 已调整为 7 天；部署后需重启后端并重新登录一次，旧 token 因没有 Redis 白名单记录不会自动迁移。

## 2026-07-15：存储健康入口收敛与真机采集定位

- 删除一级菜单“存储健康”和集群选择器，只保留“系统管理 → 存储集群”列表最后一列的既有“详情”入口。
- 详情页移除重复的集群配置摘要；导出下拉移入查询栏动作插槽，与日期范围分列布局；性能和故障空态补充采集任务与设备权限提示。
- 真机确认 NetApp `storage/volumes` 请求 `fields=uuid,name,metrics` 返回 `400/262197`，改为单数 `metric` 后返回 `200`；采集解析同步读取 `record.metric`。
- 当前数据库中 NetApp 有 `4197` 条厂商事件、Isilon 厂商事件为 `0`，两套集群的 `storage_performance_metrics` 均为 `0`。当前 Isilon 账号登录 OneFS `platform` 服务返回 `403`，三个事件/性能只读接口返回 `401`。
- 普通告警查询固定为 `source=diskpulse`；NetApp/Isilon 原生事件通过新增 `system-events` 分析接口进入故障页，不再与容量告警混排或显示为“扩容”。
- 本轮 TDD RED：前端 `5 failed, 6 passed`，后端 `2 failed, 80 passed`；GREEN 聚焦验证：前端 `11 passed`，后端 `82 passed`。
- 前端 targeted ESLint、生产构建和后端 `compileall` 通过；未登录浏览器在 `1280×720`、`768×1024`、`414×896` 下确认日期与导出不重叠，且详情页不再展示集群配置摘要。
- 外部阻塞：需为 Isilon 采集账号恢复 OneFS Platform API 登录及 event/statistics 只读权限；部署后需重启 Celery worker。当前 `celery inspect registered` 没有 worker 节点响应，尚未执行写入式采集复验。
- 既有应用壳在 `320/375px` 宽度仍因固定侧栏产生横向溢出；本轮未扩大为全局导航响应式重构，桌面与平板布局不受影响。

## 2026-07-15：修复项目组监控配置无法保存

- 根因是编辑表单复用详情响应后，PUT payload 仍包含只读 `qtree`、`in_charge_user`，与后端 `extra="forbid"` 写入契约冲突并返回 `422`。
- 表单提交前沿用现有字段清理逻辑，剔除这两个只读字段；未修改后端 API、数据库或公共请求层。
- TDD RED：聚焦测试 `1 failed, 11 passed`；GREEN：同一测试文件 `12 passed`。
- 未连接运行中的前后端执行浏览器保存冒烟；风险限于真实部署状态和数据环境，静态提交契约已由回归测试覆盖。

## 2026-07-15：过滤关闭 TLS 校验后的重复告警

- HTTPS 存储集群显式设置 `tls_verify=false` 时，保留一次 DiskPulse 风险告警，并过滤 urllib3 每次请求重复产生的 `InsecureRequestWarning`。
- HTTP 未加密告警及连接、认证、HTTP 状态错误不受影响。
- `cd backend && ..\.venv\Scripts\python.exe -m pytest test/test_storage_collection_trigger.py -q`：`7 passed`。
- Celery worker 需重启后加载修改。

## 2026-07-15：修复 AI 预建表迁移冲突

- 移除应用启动时绕过 Alembic 的 PostgreSQL `create_all()`；`database.create_tables` 仅保留 QuestDB 前向升级。
- `000000000003` 可核对并接管历史启动流程完整预建的 AI 四表，半套表或字段不匹配时拒绝继续。
- TDD RED 为 `3 failed`，GREEN 聚焦为 `4 passed`；真实 PostgreSQL 已从 `000000000002` 升到唯一 head `000000000004`。
- 当前 QuestDB 已是 `000000000003`，本次未重复执行写入式升级。

## 2026-07-15：存储集群健康分析与报表导出

### 已完成

- 已扩展 NetApp/Isilon 客户端与独立 Celery 采集任务，按分钟采集设备事件、每 5 分钟采集性能指标；现有容量采集链路保持不变。
- `storage_alerts` 已补充集群、来源、厂商事件 ID、故障指纹和标准严重级别；QuestDB 已增加保留 180 天的 `storage_performance_metrics`。
- 已增加容量变化、严重级别统计、Top 10 高延迟、重复故障和统一导出接口，并接入存储集群详情页的“容量趋势”“性能分析”“故障分析”页签。
- 页面共用时间范围并按页签懒加载；当前板块和完整报告支持 CSV、Excel、PDF，完整 CSV 以 ZIP 返回。
- 报告按需生成，不新增报告归档、定时邮件或权限体系。

### 验证状态

- TDD RED checkpoints：`e465ab9`、`4c7b7bc`、`188e5c9`、`d8c011f`、`d4c88ad`，依次锁定基础分析契约、采集器、事件去重与延迟单位、验证缺口和导出边界。
- GREEN：存储健康聚焦测试为 `79 passed`；后端完整回归为 `253 passed`，`compileall` 和 `pip check` 通过。
- 前端完整回归为 `37` 个测试文件、`177 passed`；`npm run build:prod` 通过，存储健康相关 targeted ESLint 为 `0 errors`。
- Alembic 唯一 head 为 `000000000004`，history 为 `000000000004 -> 000000000003 -> 000000000002 -> 000000000001`；MySQL、PostgreSQL offline SQL 生成通过。
- PDF 无 logo 冒烟通过，验证报告生成不依赖 logo 文件。
- 未连接真实 NetApp、PowerScale、PostgreSQL、MySQL、QuestDB 或登录浏览器；自动化测试、offline SQL 和本地 PDF 冒烟不能替代部署环境验证。

### 风险与边界

- PowerScale 需通过 `/platform/latest` 发现资源版本；早期节点降级方案已由本页顶部的 path workload 采集替代，缺少逐路径 workload 时不写入虚构的卷延迟。
- 性能历史从功能启用后开始累计，不回灌设备历史；查询和导出最多 180 天。
- 无法唯一归属存储集群的既有项目级容量告警不进入集群错误统计；重复故障仅统计 NetApp/Isilon 设备事件。
- 真实环境仍需确认设备权限、统计键及单位、事件字段、QuestDB TTL、数据库迁移和浏览器下载行为。

## 2026-07-15：AI 助手与 AI 中心

### 已完成

- 新增 `ai_configs`、`ai_conversations`、`ai_messages`、`ai_audit_logs` 及 Alembic `000000000003`；会话仅按用户隔离，不保留项目绑定。
- 支持 OpenAI、OpenRouter、Ollama、Claude，API Key 使用独立 Fernet 密钥加密，管理接口只返回掩码。
- 新增同步和 SSE 对话、最近 20 条历史、首条消息命名、4 轮工具循环、成功/失败/取消审计和敏感摘要脱敏。
- 通过 `openapi_extra.ai_exposed` 注册 30 个只读 JSON 工具，内部 ASGI 调用携带当前用户 Bearer Token；写接口、配置、用户管理、备份、导出和图片均排除。
- Redis DB 7 提供每用户每分钟 10 次固定窗口限流；Redis 不可用返回 `503`，超限返回 `429 + Retry-After`。
- 前端新增根菜单“AI 助手”和超级管理员“AI 中心”，支持会话恢复、模型选择、消息流、停止生成、失败重试、工具状态、安全 Markdown、模型管理和审计详情。
- 根菜单增加显式顺序，“AI 助手”固定显示在“项目组”之后、“告警”之前。
- 新增 `markdown-it`、`dompurify` 并更新 npm 锁文件；同步功能专题、运行配置、文档索引和最新功能。
- 补充 AI 后端与前端实现细节文档，明确 SSE 持久化边界、Provider 适配、动态工具鉴权、会话状态和 Markdown 安全约束；核心代码同步增加非显然设计注释。

### 验证状态

- RED checkpoint：后端因缺失 `AIConfig` 无法收集，前端因缺失 `@/api/ai-api` 无法编译；已单独提交 `a3e66ac`。
- GREEN 聚焦：后端 AI 测试为 `20 passed`，AI 新增模块 statements/branches 综合覆盖率 `91%`；前端 AI 交互与契约为 `9 passed`。
- 后端完整回归为 `174 passed`；`compileall` 与 `pip check` 通过。
- 前端覆盖率回归为 `168 passed`，全局 statements/lines `92.55%`；新增 `ai-api.js` 为 `95.6%`、`AiChatPage.vue` 为 `97.36%`、AI 管理页面为 `100%` 行覆盖。全量 lint 和生产构建通过。
- Alembic 唯一 head 为 `000000000003`，history 为 `000000000003 -> 000000000002 -> 000000000001`；PostgreSQL offline SQL 生成成功，并包含 4 张 AI 表。SQLite、PostgreSQL、MySQL 三方言 AI migration 编译测试通过。
- 实现文档与核心注释复验：后端 AI 测试 `20 passed`，前端 AI 测试 `9 passed`，AI 前端文件 lint 和 `git diff --check` 通过。
- 生产构建保留既有 `%VITE_APP_TITLE%` 未定义和大于 `500 kB` chunk warning；测试保留既有 Sass legacy API warning。

### 风险与后续

- 未使用真实 Provider Key、Redis 服务或登录浏览器执行集成冒烟；配置、迁移和自动化测试通过不能替代部署环境连通性验证。
- 审计首版不自动清理；上线后应结合数据保留要求评估周期清理。

## 2026-07-14：项目组标签列表布局对齐存储集群列表

### 已完成

- 将“新增标签”从筛选栏下方的独立按钮行移入表格右侧操作列表头。
- 复用存储集群列表现有的表头按钮结构，移除独立按钮行造成的额外纵向留白。
- 新增页面结构回归测试，锁定新增入口位于表头且筛选栏后不再插入独立操作行。

### 验证状态

- RED：`npx vitest run test/unit/group-tag.test.js --coverage.enabled=false`，新增用例按预期失败，`1 failed, 3 passed`。
- GREEN：同一命令通过，`4 passed`。
- `npx eslint src/pages/group-tag/GroupTagListPage.vue test/unit/group-tag.test.js`：通过。
- `npm run build:prod`：通过；保留既有的大于 `500 kB` chunk warning。

### 风险

- 未连接运行中的前后端做浏览器截图复验；本轮通过 Vue 模板结构测试和 lint 验证布局契约。

## 2026-07-14：登录认证请求去重与 LDAP 连接轻量化

### 主题

减少登录跳转和认证依赖中的重复请求、重复数据库查询，以及 ldap3 建连时无关的目录信息读取。

### 基线与根因

- 部署环境 LDAP 精确用户查询三次为 `1738.9/1548.0/1601.1 ms`，均为 `matches=1`；配置包含两个 `ldap.user_bases` 并启用 STARTTLS。
- 独立进程 PostgreSQL 用户查询 cold 为 `777.4 ms`，warm 为 `41.9–46.1 ms`，说明首个数据库连接建立也会影响冷启动请求。
- 登录页取得 profile 后，路由守卫仍会重复请求 profile；后端认证依赖和 `CurrentUserDep` 在同一请求内重复读取当前用户。
- ldap3 `Server` 使用 `get_info=ALL`，每次连接会读取本次精确用户查询不需要的目录 schema/info。

### 已完成

- 登录页取得 profile 后写入 store，路由守卫优先复用；刷新后 store 为空时仍正常请求一次 profile。
- 后端把已验证用户保存到当前 `Request` 并在同一请求内复用；每个新请求仍独立执行 JWT 校验和用户查询，不引入跨请求认证缓存。
- ldap3 `Server` 从 `get_info=ALL` 改为 `NONE`，保留 STARTTLS、CA 证书校验、连接超时和 TLS-before-bind。

### 验证状态

- 后端 RED 为 `2 failed, 14 passed`；GREEN 聚焦回归为 `43 passed`。
- 前端 RED 为 `1` 个预期失败，刷新后加载 profile 的既有用例通过；GREEN 聚焦回归为 `4 passed`。
- 后端完整回归为 `154 passed`，`compileall` 和 `pip check` 通过。
- 前端完整回归为 `155 passed`，lint 和 `build:prod` 通过；构建仅保留既有的大于 `500 kB` chunk warning。
- 优化后部署环境 LDAP 精确用户查询三次为 `651.4/353.6/366.4 ms`，均为 `matches=1`。
- 尚未使用真实密码测量用户 bind 在内的完整登录耗时，浏览器真实登录冒烟待最终验证。

### 风险与后续

- 两组 LDAP 数据是组件级顺序测量，会受目录服务和网络波动影响，不能替代完整登录链路监控。
- 数据库 cold 查询仍明显慢于 warm 查询；只有生产首请求持续成为问题时再评估连接预热，不为单次测量新增缓存或后台任务。

## 2026-07-14：存储集群协议与 TLS 校验改为逐集群配置

### 主题

移除全局 YAML `storage.tls_verify`，让每个 NetApp/Isilon 集群独立配置设备访问协议和 TLS 证书校验。

### 已完成

- `storage_clusters` 新增非空字段 `protocol`、`tls_verify`；协议只允许 `http/https`，HTTP 下 TLS 校验不适用。
- Alembic 新增 `000000000002_storage_cluster_transport.py`：已有行迁移为 `https/false`，新建集群默认 `https/true`，当前唯一 head 为 `000000000002`。
- 全局 YAML `storage.tls_verify` 已删除；NetApp/Isilon 采集客户端和 Isilon Quota 手工检查均读取数据库中的逐集群配置。
- 存储集群新增、编辑、列表和详情页面展示并提交访问协议和 TLS 校验；选择 HTTP 时自动关闭 TLS 校验。
- API 示例中的 `http://localhost:8000` 仅代表 DiskPulse API 地址，不代表设备协议。

### 验证状态

- 后端全量测试通过：`152 passed`，coverage `86%`；`compileall`、`pip check` 通过。
- 前端全量测试通过：`153 passed`，coverage statements/lines `91.93%`、branches `82.83%`；lint 和 `build:prod` 通过。
- 本地未登录浏览器冒烟确认存储集群列表出现“协议”“TLS 校验”列；新增表单默认 HTTPS 且开启 TLS 校验，切换到 HTTP 后 TLS 开关自动关闭并禁用。
- Alembic `heads` 通过，当前唯一 head 为 `000000000002`。
- SQLite online migration 的 upgrade、已有行 `https/false` 回填、新行 `https/true` 默认值和 downgrade 通过；SQLite、PostgreSQL、MySQL offline SQL 编译通过，并确认 `DEFAULT true` 与旧行 `UPDATE false`。
- 尚未在真实 PostgreSQL/MySQL 执行迁移，未验证真实 NetApp/Isilon 的 HTTP/HTTPS 组合；浏览器因当前无登录会话未取得数据，真实数据列表、编辑和详情仍待登录环境验证。

### 风险与后续

- 已有集群继续使用 `https/false`；应在设备证书受运行环境信任后逐集群开启 TLS 校验。
- HTTP 不提供传输加密，设备凭据会以明文传输，只应在可信隔离网络中使用。

## 2026-07-14：用户信息管理与 LDAP 一键同步

### 主题

复用 `/admin/users` 建设超级管理员用户维护页面，并通过完整 LDAP 快照同步系统用户资料和离职/在职生命周期。

### 已完成

- 明确用户类型为 `0=离职`、`1=公共用户`、`2=在职`，保持现有模型默认值和数据库结构，不新增 migration。
- 新增超级管理员接口 `POST /storage-pulse/api/users/sync-ldap`，返回 `ldap_total`、`created`、`updated`、`reactivated`、`marked_inactive`。
- LDAP 新用户创建为在职；重新出现的离职用户恢复在职；快照缺失的在职用户转为离职；同步不删除用户。
- 公共用户类型不由 LDAP 修改，缺失时不受影响；LDAP 中存在时可更新非空姓名、邮箱和部门。
- 空快照、不完整搜索范围和忽略大小写的用户名冲突会拒绝同步并回滚。
- 修复多 LDAP 搜索范围登录：单用户查询会跳过无匹配范围并继续查找，完整同步的快照保护保持不变。
- 用户页面补齐查询、新增、编辑、删除和同步操作；登录用户名创建后不可修改，姓名、邮箱、部门、用户类型和告警状态可人工维护。
- 新增 `ldap.user_department_attribute`，默认 `department`；真实 `backend/config.yml` 继续保持本地，目录字段不同时由部署侧调整。
- 同步用户管理专题、LDAP 认证配置、文档索引和最新功能说明。

### 验证状态

- 后端用户管理与 LDAP 分支测试通过，`35 passed`；`usersService` 分支覆盖率 `96%`，`ldap_directory` 分支覆盖率 `95%`。
- 认证、用户管理与 LDAP 同步聚焦回归通过，`41 passed`；后端 `pip check` 和 `compileall` 通过。
- 前端功能与相关回归测试通过，`18 passed`；`lint` 和 `build:prod` 通过。
- Vitest 全局测试超时统一为 `15s`；默认 `npm test` 和 `npm run test:coverage` 均为 `150/150` 通过。
- 前端总 `lines/statements` 为 `91.88%`、`branches` 为 `82.1%`，用户页为 `91.24%`、表单为 `96.57%`，`users-api` 和 `routes` 为 `100%`。
- `git diff --check` 通过，仅有 LF→CRLF 提示。

### 风险与后续

- 尚未连接真实 LDAP 验证多搜索范围、部门属性权限和大目录请求耗时；部署前需确认 `ldap.user_department_attribute` 与目录实际字段一致。
- 本轮不包含定时同步、后台任务、同步历史表、预演接口或 LDAP 同步删除；只有出现同步超时或审计需求时再评估扩展。

## 2026-07-14：存储一览按集群查看

### 主题

为“存储一览”增加存储集群选择，按目标集群加载 Volume/Qtree 容量树。

### 已完成

- 页面复用 `StorageClusterSelect`，选择或清空集群时自动刷新 treemap。
- `/aggregates/storage-trees/` 新增可选 `storage_cluster_id`，并在数据库查询阶段过滤 Volume。
- `storage_cluster_id` 使用 `Query(ge=1)` 校验，非法非正整数返回 `422`。
- 修正页面加载态变量名，使切换集群期间正确显示加载状态。

### 验证状态

- RED：前端首次请求仍为 `{}`；后端传 `storage_cluster_id=2` 仍返回两个集群的 Volume。
- GREEN：页面聚焦 Vitest 通过，`1 passed`；`backend/test/test_core_api.py` 通过，`8 passed`。
- `.\.venv\Scripts\python.exe -m compileall -q backend` 与 `npm run build:prod`：通过。

### 风险与后续

- 未连接真实 NetApp/Isilon 数据或执行浏览器端到端测试；实际大数据量 treemap 切换待集成环境确认。
- 构建仍有既有 Sass legacy API deprecation 和大于 `500 kB` chunk warning，本次未处理。

## 2026-07-14：隐藏离职备份前端入口

### 主题

仅在前端隐藏离职备份页面入口、配置项和操作入口，保留现有页面、路由、字段绑定、调用逻辑和后端能力。

### 已完成

- 为 `/admin/backup` 路由增加 `meta.isHidden`，系统管理菜单不再展示“离职备份”，路由和 `BackUpListPage.vue` 保持注册。
- 隐藏系统设置中的“目录操作和备份配置”页签。
- 隐藏项目组列表中的离职备份列、项目组表单中的离职备份开关、项目组详情中的备份路径，以及用户目录列表中的“移至备份”按钮。
- 保留 `confirmBackUp`、备份配置字段绑定、备份页面操作和全部 API 调用代码；保存其他系统设置时，隐藏的备份配置值保持不变。
- 新增前端可见性契约，覆盖菜单、设置、项目组列表/表单/详情和用户目录操作六个展示面。

### 验证状态

- RED：新增可见性契约在六个展示面按预期失败；旧设置页测试因仍操作已隐藏的数字框和开关失败。
- GREEN：`npx vitest run test/unit/offboarding-backup-visibility.test.js test/unit/settings-config.test.js test/unit/router/routes.test.js test/unit/components/dialog-function-coverage.test.js test/unit/smoke/components-and-pages.test.js --coverage.enabled=false` 通过，`5` 个文件、`19` 个测试。
- `npm run lint`：通过。
- `npm run build:prod`：通过；仍有既有 Sass legacy API deprecation 和大于 `500 kB` chunk 警告，本次未处理。

### 风险与后续

- 本次仅隐藏前端展示，不是权限控制；直接访问 `/admin/backup` 仍可加载原页面，后端接口行为未变。
- 未执行真实浏览器端到端测试，菜单和各页面的最终视觉结果待集成环境确认。

## 2026-07-14：统一 NetApp/Isilon 存储资源术语与采集

### 主题

统一 NetApp 与 Isilon 的容量池、存储空间、Qtree（NetApp）、用户用量和项目组绑定语义，并让采集、汇总、接口和页面使用同一映射。

### 已完成

- Isilon 使用 OneFS 9.11 `/platform/16/storagepool/storagepools?toplevels=true` 采集真实 Storage Pool 并写入 `Aggregate`；Directory Quota 写入 `Volume`，类型为 `directory_quota`。
- 同一轮 Isilon 采集复用一次 quota 响应生成存储空间和用户配额；cluster stats 只更新集群总容量，不再生成 `isilon_cluster` Aggregate。
- NetApp 只保存真实 Qtree；成功采集后把历史 `null` Qtree 项目组绑定迁移到对应 `volume_id`，再清理占位记录。
- 项目组汇总支持 NetApp Volume、NetApp Qtree 和 Isilon Directory Quota；项目汇总按集群、目标类型和目标 ID 去重直接目标。
- `GET /groups` 新增 `volume_id` 过滤；与 `qtree_id` 同时提交时返回 `422`。
- 前端路由、列表、详情、选择器、项目组、用量和告警统一使用“容量池”“存储空间”“Qtree（NetApp）”，厂商原生类型由现有字段派生。
- 保留 `Aggregate`、`Volume`、`Qtree` 模型、枚举和 API 路径；未新增 PostgreSQL、Alembic 或 QuestDB schema，QuestDB 当前 head 仍为 `000000000002`。
- Isilon 未启用会话缓存时按 OneFS 规范显式注销服务端会话；注销失败不覆盖采集结果，并始终关闭本地 HTTP session。
- `backend/scripts/manual_isilon_check.py` 支持按存储集群名称读取数据库中的 Isilon 连接配置，只读获取 Quota 并输出总数和类型统计。
- 更新领域术语、资源映射、API 示例、迁移说明、最新功能和存储集群专题索引。

### 验证状态

- 后端聚焦测试：`9 passed`；完整后端：`122 passed`；覆盖率 `84%`。
- 后端 `compileall`、`pip check`、Alembic `heads` 通过。
- 前端默认 `npm run test:coverage` 已为 `150/150` 通过；全局测试超时统一为 `15s`。
- 前端覆盖率为 Statements/Lines `91.88%`、Branches `82.10%`、Functions `69.75%`；`npm run lint` 和 `npm run build:prod` 通过。
- 登录态 Chrome 冒烟通过容量池、存储空间、Qtree（NetApp）、项目组页面和 NetApp 存储目标选项；未发现页面级横向溢出。
- Isilon 节点管理入口已确认集群身份和 OneFS `9.11.0.5`；Storage Pool 接口返回 `2` 个真实 Node Pool，Quota 接口完成 `3` 页、`2264` 条数据的读取，其中 `64` 条为 Directory Quota。
- 新增会话注销 RED/GREEN 测试；会话关闭聚焦测试 `3 passed`，资源映射测试文件 `19 passed`。
- 配置驱动的 Isilon Quota 手工检查脚本聚焦测试 `3 passed`，脚本 `compileall` 通过；使用部署数据库中的原 Isilon 配置真机执行成功，读取 `2264` 条 Quota：`40` 条 default-user、`64` 条 directory、`2160` 条 user。

### 风险与后续

- 已确认当前账号启用、未锁定、密码未过期，且角色权限覆盖 Platform API、Cluster、SmartPools 和 Quota；无需以“补充 PAPI 权限”为前提继续排查。
- 部署数据库中的原 Isilon 连接入口已通过 PAPI 登录和 Quota 分页验证，无需为本次 Quota 采集切换入口。
- 真机 Storage Pool 条目未返回 SDK 中定义为可选的 `usage` 对象，当前实现缺少容量池总容量和已用容量来源；确认官方字段来源和权限影响前，整集群采集仍保持回滚保护。
- 尚未在持有历史 `isilon_cluster`/`null` Qtree 数据的集成 PostgreSQL 和 QuestDB 环境观察完整采集事务；QuestDB 历史占位指标按设计保留。
- Directory Quota 与 Storage Pool 不保证一对一；无法确认唯一归属时 `Volume.aggregate` 保持为空。
- 当前真机集群关闭 TLS 证书校验时会产生 `InsecureRequestWarning`；生产环境应配置可信 CA 并逐集群启用校验。

## 2026-07-14：存储资源按集群筛选

### 主题

在 Volume、聚合和 Qtree 列表筛选栏增加存储集群下拉框，按所属集群查询对应资源。

### 已完成

- 三个列表统一复用 `StorageClusterSelect` 的远程搜索、清空和默认选项加载能力。
- Volume、聚合和 Qtree 列表请求新增 `storage_cluster_id` 筛选参数；重置后恢复为 `null`。
- 页面级测试参数化覆盖三个列表的初始请求、选择集群后搜索和重置清空。

### 验证状态

- RED：Volume 初始用例因仍包含 `project_id` 且缺少 `storage_cluster_id` 失败；扩展用例后，聚合和 Qtree 因缺少该参数失败。
- GREEN：`.\node_modules\.bin\vitest.cmd run test/unit/pages/volume-list-page.test.js --coverage.enabled=false` 通过，`3 passed`。
- `npm run build:prod`：通过；仍有既有的 chunk 大于 `500 kB` warning，本次未处理。

### 风险与后续

- 未连接真实后端或运行浏览器端到端测试；三个列表的下拉选项加载和实际集群过滤待集成环境确认。

## 2026-07-14：集群配置后自动同步卷信息

### 主题

启用的 NetApp 或 Isilon 集群在创建、更新后立即投递对应集群的卷采集任务。

### 已完成

- 存储集群创建、更新接口在事务提交后按最终 `is_active` 状态投递异步采集；未启用集群不投递。
- 复用 `storages_schedule_fetching_task` 和 `StoragePulseMonitor`，新增可选 `storage_cluster_id` 过滤，不新建第二套设备采集逻辑。
- Celery 依赖声明改为 `celery[redis]`，补齐现有 Redis broker/lock 代码的 transport 依赖。
- 存储集群新增/编辑表单新增“是否启用”开关，新建默认启用并提交 `is_active` 布尔值。
- API 调度使用 Uvicorn logger 记录投递开始、成功和失败；Celery worker 记录任务开始，日志不包含设备凭据。
- Celery 实例及任务装饰器统一使用 `diskpulse_app`，Windows 和 Linux 启动入口显式指定 `celery_worker:diskpulse_app`。
- 当时新增全局 `storage.tls_verify` 布尔配置并默认设为 `false`；该配置现已被逐 `StorageCluster` 的 `protocol`、`tls_verify` 字段取代并从 YAML 删除。
- 存储 API 连接或 HTTP 失败改为向上抛出，由现有集群事务回滚，避免空结果删除已有 Volume/Qtree。

### 验证状态

- RED：集群 CRUD 聚焦测试 3 个用例因缺少调度行为失败；定向快照测试因不支持 `storage_cluster_id` 失败。
- GREEN：`.\.venv\Scripts\python.exe -m pytest backend\test\test_storage_soft_quota.py backend\test\test_core_api.py backend\test\test_storage_collection_trigger.py -q` 通过，`13 passed`。
- `.\.venv\Scripts\python.exe -m pip check` 与 `.\.venv\Scripts\python.exe -m compileall -q backend`：通过。
- 任务范围 coverage：`storage_cluster.py` `92%`、`storageClusterService.py` `100%`，合计 `93%`。
- `.\node_modules\.bin\vitest.cmd run test/unit/components/dialog-function-coverage.test.js --coverage.enabled=false`：通过，`7 passed`。
- `.\.venv\Scripts\python.exe -m coverage run -m pytest backend\test\test_storage_collection_trigger.py backend\test\test_core_api.py -q`：通过，`10 passed`；目标模块合计覆盖率 `93%`。
- `npm run build:prod`：通过；仍有既有的 chunk 大于 `500 kB` warning，本次未处理。
- RED：Celery 应用命名契约因仍定义 `lsf_app` 失败；GREEN：命名契约与采集调度聚焦测试 `4 passed`，`diskpulse_app` 导入和任务注册检查通过。
- TLS 配置与失败回滚 RED 为 `6 failed`，布尔值校验 RED 为 `1 failed`；同组 GREEN 为 `7 passed`。
- `.\.venv\Scripts\python.exe -m pytest backend\test\test_app_config.py backend\test\test_storage_collection_trigger.py backend\test\test_security_regressions.py backend\test\test_storage_soft_quota.py -q`：通过，`30 passed`。

### 风险与后续

- 未连接真实 NetApp、Isilon、Redis 或 Celery worker；真实设备卷数据和任务消费链路待部署环境验证。
- 任务投递失败不会回滚已保存配置，错误写入服务端日志，后续周期采集继续兜底。
- 当时默认关闭 TLS 证书校验会降低中间人攻击防护；当前应在设备证书受信任后逐集群将 `tls_verify` 改为 `true`。

## 2026-07-14：项目组标签与直接资源绑定

### 主题

删除项目级存储环境关系，将其收敛为只包含名称的全局 `GroupTag`；`Group` 直接绑定项目、存储集群和标签。

### 已完成

- `group_tags` 只保留 `id`、`name`，名称全局唯一；标签不绑定项目或存储集群，也不保存容量、状态或采集时间。
- `groups` 直接保存非空的 `project_id`、`storage_cluster_id`、`group_tag_id`，并继续严格校验 Volume/Qtree 必须属于所选集群。
- 新增 `/storage-pulse/api/group-tags` 全局 CRUD；标签写操作要求超级管理员，重复名称和删除已引用标签返回 `409`。
- 采集、告警、Usage、备份和周报改为读取 Group 的直接关系；删除环境级 QuestDB、汇总、告警和实时趋势语义。
- 前端新增“项目组标签”管理页和选择器；项目组表单分别选择项目、存储集群、标签，项目详情和 Dashboard 按 Group 直接展示。
- 单一 Alembic baseline 已改写；不提供旧 `project_storage_environments` 数据兼容或回填。

### 验证状态

- 后端 `python -m pytest backend/test -q`：`66 passed`；`python -m compileall -q backend`：通过。
- 前端 `.\\node_modules\\.bin\\vitest.cmd run --testTimeout=15000`：`25` 个测试文件、`126 passed`；`npm run build:prod`：通过。

### 风险与后续

- 使用旧 baseline 的开发数据库不能原地升级，需确认数据可丢弃后重建空库。
- 未连接真实 PostgreSQL、QuestDB、NetApp、Isilon 或 Celery worker 做端到端验证。

## 2026-07-14：QuestDB 版本管控与启动初始化

### 主题

将当前 `7` 张 QuestDB 趋势表纳入独立前向 revision 管控，并替换启动时无版本记录的 `QuestDBBase.metadata.create_all()`。

### 已完成

- 新增 `backend/questdb/migrations/000000000001_initial_schema.sql`，结构与当前 `QuestDBBase.metadata` 一致。
- 新增 `backend/questdb/migrate.py`，提供 `history/current/upgrade`，通过 `diskpulse_schema_migrations` 记录版本、SHA-256 checksum 和应用时间。
- `database.create_tables=true` 时启动自动执行 QuestDB upgrade；重复执行跳过已应用 revision，checksum 漂移和本地未知 revision 会失败。
- QuestDB 采用前向、幂等 migration，不模拟其不支持的 PostgreSQL 主键、事务回滚或 PGWire `DELETE`。

### 验证状态

- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend\test\test_questdb_migrations.py -q`：通过，`12 passed`；任务专用 coverage 配置下 `backend/questdb/migrate.py` statements/branches 综合覆盖率 `98%`。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend\test -q`：通过，`158 passed`、`41` 个既有弃用 warning；`compileall -q backend` 通过。
- PostgreSQL Alembic `heads/history`：通过，唯一 root/head 为 `000000000001`。
- 使用当前配置导入 `main`：启动迁移成功；QuestDB 的 `7` 张业务表逐列与 `QuestDBBase.metadata` 一致，版本账本存在。
- 当前配置 QuestDB：`history/current/upgrade/current` 通过，revision 为 `000000000001`；共 `8` 张表，包括 `7` 张趋势表和 `diskpulse_schema_migrations`；重复升级返回 `up to date`。

### 风险与后续

- 尚未在独立空白 QuestDB 实例执行从 `base` 到 head 的录像式验收；当前实例的首次创建可能由运行中的自动重载服务触发。
- QuestDB migration 不提供自动 downgrade；破坏性回退必须先备份，再使用独立修复 revision 或重建实例。
- 多副本生产部署应由单一迁移节点先执行 `python -m questdb.migrate upgrade`，再启动 API/worker，避免并发执行未来可能不具备天然幂等性的 DDL。

## 2026-07-13：项目存储环境分层、绑定与采集隔离（已废弃）

> 该方案已由 2026-07-14 的 `GroupTag + Group` 直接绑定模型替代，仅保留为历史交付记录。

### 主题

在 `Project` 与存储资源之间引入 `ProjectStorageEnvironment`，统一项目、存储集群、项目组和 Volume/Qtree 的绑定关系，并按项目存储环境提供管理、工作台、汇总和实时趋势能力。

`docs/features/project-storage-environment/design.md` 已按当前绿地实施方案收敛重写；当前分支的实际实施与验收状态以该设计、代码和自动化测试为准。

### 已完成

- 新增 `ProjectStorageEnvironment` 关系模型；Alembic 只保留 root/head `000000000001`，从空库一次创建当前 `14` 张表和 `31` 个索引。`groups.project_environment_id` 从建表起为 `NOT NULL`，不存在重复的 `project_id/storage_cluster_id` 物理列；项目内环境名称、项目与集群组合均保持唯一。
- 新增项目存储环境列表、创建、详情、摘要、实时趋势、更新和删除 API；读操作按超级管理员、项目负责人或 PT 负责人校验项目访问权，写操作要求超级管理员。已绑定项目组的环境拒绝删除。
- 项目组 API 支持按 `project_environment_id` 过滤，并要求写入时选择一个环境以及且仅一个 Volume/Qtree 目标；目标必须属于环境绑定的存储集群，Isilon 环境只允许 Volume。
- 前端完成项目存储环境 CRUD、项目组级联绑定、项目详情工作台和 Dashboard 环境维度接入。项目列表展示环境数量、集群类型和状态统计；工作台按启用环境切换，展示环境摘要、实时趋势和关联项目组，并通过 `environment_id` 保持可分享的当前环境状态；Dashboard 支持项目/环境筛选、环境独立容量展示，并使用 `project_environment_id:group_id` 稳定 key 隔离跨环境同名 Group。
- Usage、Alert 和导出完成环境筛选、环境内 Group 约束与环境列；监控/扩容下游统一解析 Volume/Qtree 目标，备份路径增加环境目录，项目周报按环境分组。
- Celery 存储采集每轮先加载新的、与 ORM session 解耦的标量快照；任务通过稳定 ID 和短会话读取当前数据库绑定，后续按存储集群创建独立 session 和事务。单集群 PostgreSQL 更新提交后再写 QuestDB，QuestDB 写入失败不会回滚已提交的 PostgreSQL 数据。
- Group/User/Project/System 告警、项目周报、单次与批量备份、BPM 和删除流程批量预加载关联并复用当前 ORM 快照；Group TOP20 使用一次窗口查询，`enable_monitoring=false` 的 Group 不进入 Group/User 告警。该口径仅覆盖本次主链路，不代表整个 `celery_tasks` 目录已消除 N+1。
- 采集轮次允许部分集群失败并保留成功集群结果；只有全部集群失败时轮次失败。项目级汇总只在该项目全部启用环境于本轮完整成功时更新，避免部分成功覆盖完整项目统计。
- Isilon 项目组直接绑定 Volume，不再创建或依赖 `name='null'` 的 Qtree；环境汇总按真实 Volume/Qtree/多用户项目组目标去重，多个项目组指向同一目标时只计一次。
- 项目组创建、更新和响应不接受或返回旧 `project_id/storage_cluster_id` 数字字段；保留的项目/集群列表筛选参数通过 `ProjectStorageEnvironment` 关系查询，不做兼容双写。

### 验证状态

- `& 'D:\dev\DiskPulse\.venv\Scripts\python.exe' -m pytest backend\test -q`：通过，`146` 个测试，`41` 个既有弃用 warning。
- `& 'D:\dev\DiskPulse\.venv\Scripts\python.exe' -m coverage run -m pytest backend\test -q; & 'D:\dev\DiskPulse\.venv\Scripts\python.exe' -m coverage report`：通过，`2892` statements、`444` miss，总覆盖率 `85%`。
- migration 独立审计：versions 恰好 `1` 个，`000000000001` 为 root/head；SQLite upgrade 后与 `Base.metadata` 对比无差异，downgrade 后 `0` 张表；PostgreSQL offline upgrade/downgrade DDL、逆序 drop、`heads/history`、`compileall` 和 diff check 通过，核心迁移测试 `13 passed`。
- MySQL 全 `Base.metadata` 编译审计未通过：当前 `14` 张表中 `13` 张因无长度 `String/VARCHAR` 触发 `CompileError`。本次 baseline 仅声明支持 SQLite/PostgreSQL，未满足后端开发标准的默认三方言编译门禁。
- `cd frontend; .\node_modules\.bin\vitest.cmd run --testTimeout=15000`：通过，`30` 个测试文件、`153` 个测试。
- `cd frontend; .\node_modules\.bin\vitest.cmd run --coverage --testTimeout=15000`：通过；`statements 93.47%`、`branches 83.56%`、`functions 82.11%`、`lines 93.47%`。
- `cd frontend; npm run lint`：通过。
- `cd frontend; npm run build:prod`：通过。

### 风险与后续

- 当前项目仍处于初始开发阶段，不实现历史数据回填、字段兼容窗口或 M3；已删除旧 revision 和回填脚本。
- 已使用删除前 revision 的开发数据库不支持原地升级；确认数据可丢弃后重建空库，再执行 `000000000001`。不得伪造 `alembic_version` 接续旧链。
- 未连接真实 PostgreSQL、QuestDB、NetApp 或 Isilon 做端到端验证；外部连接、实际设备返回、QuestDB 表结构和跨库最终一致性仍需在集成环境验收。
- 当前 baseline 未支持 MySQL：全 metadata 编译时 `14` 张表中 `13` 张失败；若后续把 MySQL 纳入部署范围，需要先统一补齐无长度 `String/VARCHAR` 的长度并重新通过三方言门禁。
- 未执行外部浏览器 smoke；当前结果不包含仓库外浏览器交互或 E2E 验收。
- `StoragePulseMonitor` 的结果正确性已有测试覆盖，但尚未按生产数据规模做性能压测；无生产入口的旧 monitor 已删除。
- 当前 `backend/celery_worker.py` 只启用 60 秒一次的 `storages_schedule_fetching_task`；告警、周报和定时备份 beat 条目仍为注释状态，优化后的路径尚未通过真实 Celery beat/worker 调度验收。
- `npm run build:prod` 虽成功，但仍有既有的 `VITE_APP_TITLE` 未定义和 chunk 大于 `500 kB` warning，本次未处理。
- 本次自动化测试覆盖模型、迁移契约、API、前端交互、采集事务和聚合边界，不等同于生产容量数据验收。

## 2026-07-13：项目未使用字段审计与清理

### 已完成

- 审计 `backend/models.py` 的 `14` 个 ORM 模型、`221` 个数据库字段，并追踪后端 CRUD/service/Celery 与前端 `frontend/src` 的生产引用。
- 形成 `docs/tracking/unused-field-audit-2026-07-13.md`：记录 `20` 个无业务读写字段、`4` 个运行时不生效的 QuestDB 重复配置字段和 `1` 个无业务语义的单例配置名称字段。
- 复核 `ProjectStorageEnvironment` 新增字段；身份、绑定、容量、采集状态和最近成功采集时间均有明确链路，未发现可直接删除的环境核心字段。
- 已从 ORM、Pydantic schema 和数据库迁移删除 `20` 个无业务读写字段；备份生命周期继续只使用 `status`。
- 已从 `StorageConf`、配置 API schema 和设置页面删除 `4` 个运行时不生效的 `questdb_*` 字段；QuestDB 连接继续只读取 `backend/config.yml` 的 `database.questdb`。
- 这 `24` 个字段已从当前 ORM 和单一 initial baseline 中移除；没有独立清理 revision、历史数据回填、废弃兼容层或动态重连逻辑。
- `StorageConf.name` 属于单独的无业务语义结构字段，不在本轮指定的两类删除范围内，继续保留。

### 验证状态

- 已通过精确字段搜索核对候选字段的声明、业务读写和前端展示位置。
- 已复核 `backend/appConfig.py`、`backend/questdb/database.py` 和 `backend/dependencies.py`，确认 QuestDB 连接只读取 `config.yml`，不会读取 `StorageConf.questdb_*`。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test/test_backend_schema_contract.py backend/test/test_security_regressions.py backend/test/test_core_api.py -q`：通过，`20` 个测试；其中 baseline 在临时 SQLite 完成 upgrade/downgrade，并通过 PostgreSQL offline DDL 编译检查。MySQL 全 metadata 编译不在通过范围内。
- `cd frontend; npx vitest run test/unit/settings-config.test.js --coverage.enabled=false`：通过，`2` 个测试。
- 最终全量验证：后端 `146 passed`、`41 warnings`，覆盖率 `85%`（`2892` statements、`444` miss）；前端 `30` 个测试文件、`153 passed`，覆盖率 statements `93.47%`、branches `83.56%`、functions `82.11%`、lines `93.47%`。
- `cd frontend; npm run lint`：通过。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini heads` 和 `history`：通过，唯一 root/head 为 `000000000001`；`compileall -q backend` 通过。
- `cd frontend; npm run build:prod`：通过；仍有既有的 `%VITE_APP_TITLE%` 未定义和大 chunk 警告。
- 尚未在真实 PostgreSQL 空库执行 initial baseline upgrade/downgrade；当前仅完成 SQLite 往返和 PostgreSQL offline DDL 验证。

## 2026-07-13：登录后 profile 请求补齐 Bearer scheme

- 修复前端请求拦截器发送裸 JWT，导致登录成功后 `/users/current/profile` 返回 `401` 的问题。
- 有 token 时统一发送 `Authorization: Bearer <token>`；登录响应和 profile API 契约不变。
- `npx vitest run test/unit/api/support.test.js test/unit/auth-login.test.js`：通过，3 个测试。

## 2026-07-13：LDAP 登录失败日志补齐

### 已完成

- 确认服务账号 STARTTLS、bind 和用户查询正常，`guojianpeng` 可被目录检索到；登录失败发生在用户账号 bind 阶段。
- 用户 STARTTLS 或 bind 被拒绝时记录 LDAP result code/description，异常时仅记录异常类型；日志不包含用户名、DN 或密码。
- LDAP 失败日志改由 `uvicorn.error` 输出，确保开发环境控制台可见。
- 目录查询无匹配用户时补充独立 warning，与用户 bind 被拒绝日志明确区分。
- 登录接口仍统一返回 `401 invalid credentials`，不向客户端泄露认证细节。

### 验证状态

- `..\.venv\Scripts\python.exe -m pytest test\test_auth_ldap.py -q`：通过，7 个测试。

## 2026-07-13：后端运行配置迁移为分类 YAML

### 主题

移除后端应用对 `.env`、`python-dotenv` 和运行时环境变量的依赖，将运行配置统一迁移到按子系统分类的 `backend/config.yml`。

### 已完成

- 新增 PyYAML 配置加载器，支持点分路径读取、显式测试配置、URL 凭据转义、相对密码文件和非法配置快速失败。
- PostgreSQL、QuestDB、Redis、JWT、LDAP、超级管理员、CORS、建表、连接池和 Isilon 缓存均改读 YAML；手工设备检查脚本继续使用环境变量。
- 本地配置迁入被忽略的 `backend/config.yml`，LDAP 使用 STARTTLS，超级管理员为 `guojianpeng`；旧 `development.env`、`test.env` 已移除。
- 新增 `backend/config.example.yml`、`backend/config.test.yml` 和配置契约测试，移除 `python-dotenv` 依赖。
- 同步认证和后端架构文档；登录 API、JWT 响应、前端契约和数据库结构未变。

### 验证状态

- `.\.venv\Scripts\python.exe -m pytest backend\test\test_app_config.py backend\test\test_auth_ldap.py backend\test\test_auth_api.py backend\test\test_security_regressions.py -q`：通过，28 个测试。
- `.\.venv\Scripts\python.exe -m pytest backend\test -q`：通过，42 个测试。
- `.\.venv\Scripts\python.exe -m coverage run -m pytest backend\test -q; .\.venv\Scripts\python.exe -m coverage report`：通过，总覆盖率 `83%`，`backend/appConfig.py` 覆盖率 `93%`。
- `.\.venv\Scripts\python.exe -m compileall -q backend`、`.\.venv\Scripts\python.exe -m pip check`：通过。
- 静态扫描确认除 `backend/scripts/manual_*_check.py` 外，后端 Python 代码不再读取环境变量；活动代码和功能文档不再引用旧 env 配置键。
- 本地 `backend/config.yml` 已验证可加载，验证过程未输出密码或密钥。

### 风险与后续

- 未连接真实 LDAP、PostgreSQL、QuestDB、Redis、NetApp 或 Isilon；外部服务连通性与证书链待部署环境验证。
- `ldap.group_bases` 当前仅保留配置，不参与角色或权限映射。

## 2026-06-30：后端 pytest 迁移与 80% 覆盖率门禁

### 主题

将后端测试入口从 `unittest` 迁移到 `pytest`，补充核心 CRUD 和汇总逻辑测试，并把当前 `.coveragerc` 后端整体覆盖率门禁提升到 `80%`。

### 已完成

- 新增 `pytest.ini`，默认收集 `backend/test` 下的 `test_*.py` 测试。
- 新增 `backend/test/conftest.py`，统一提供内存 SQLite、数据库会话、FastAPI `TestClient`、认证头和 JWT 撤销状态隔离 fixture。
- 将 `backend/test` 下既有测试改为 pytest 函数/测试类，移除 `unittest.TestCase`、`setUp/tearDown` 和 `self.assert*` 断言风格。
- 新增 `backend/test/test_crud_pytest.py`，覆盖项目、用户、aggregate、volume、qtree、group 的 CRUD、过滤排序、树形汇总、实时数据代理和非法字段拒绝。
- 在 `backend/requirements.txt` 中新增 `pytest==9.1.1`，并将 `.coveragerc` 的 `fail_under` 提升到 `80`。

### 验证状态

- `.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`：通过。
- `.\.venv\Scripts\python.exe -m pytest backend\test`：通过，33 个测试。
- `.\.venv\Scripts\python.exe -m coverage run -m pytest; .\.venv\Scripts\python.exe -m coverage report`：通过，总覆盖率 `82%`。
- `.\.venv\Scripts\python.exe -m compileall -q backend`：通过。

### 风险与后续

- 当前 80% 覆盖率口径沿用 `.coveragerc`，仍排除外部设备客户端、QuestDB、Celery、迁移和手工脚本。
- 测试运行仍会输出 SQLAlchemy/Pydantic 迁移类弃用告警，本轮未处理这些生产代码告警。
- 本轮未连接真实 NetApp/Isilon/LDAP/QuestDB 环境，仅验证自动化测试和内存 SQLite 覆盖路径。

## 2026-06-30：后端安全审查问题修复

### 主题

修复后端安全审查中确认的敏感信息泄露、远程命令拼接、动态查询字段、TLS 默认值、异常响应、认证授权、运行时默认值和测试装配问题。

### 已完成

- 新增 `backend/test/test_security_regressions.py`，覆盖配置响应去密、存储集群响应去密、异常响应不泄露内部文本、JWT header 校验、NetApp TLS 默认开启和远程 shell 参数引用。
- `/config/storage` 响应改用 public schema，保留内部 full schema 给服务和更新入参使用。
- `StorageCluster` public 响应不再包含 `storage_password`，创建/更新入参仍允许提交密码。
- 通用异常处理不再把内部异常字符串或 Pydantic `errors` 返回给客户端。
- JWT 解码新增 header `alg=HS256`、`typ=JWT` 校验。
- NetApp/Isilon 客户端默认开启 TLS 证书校验，不再全局屏蔽 `InsecureRequestWarning`。
- 远程文件管理和 NetApp quota 扩容命令对路径、用户名、卷名、Qtree 名和目标名做 shell 参数引用，权限值限制为数字模式。
- QuestDB 动态表前缀、指标列和树图 `value_type` 改为白名单；时间和 id 使用绑定参数。
- 列表排序字段统一走 `utils.query.get_sort_column`，非法字段返回 `400`。
- 后台文件任务不再复用请求 Session，改为任务内创建独立数据库会话。
- CORS 默认收紧为本地开发源，部署可通过 `DISKPULSE_CORS_ORIGINS` 配置。
- 启动日志中的 Postgres/QuestDB URL 改为脱敏摘要；`alembic.ini` 移除硬编码内网账号密码，迁移运行时从 `appConfig` 注入 URL。
- 扩容接口改为 Pydantic schema 入参校验，失败返回 `400`，不再记录原始请求体。
- 核心 API 测试装配补齐主路由认证依赖，并使用默认测试 token。
- `Authorization` 请求头收紧为 `Bearer <token>`；裸 token 不再兼容。
- `/users/logout` 要求有效 Bearer token，并撤销当前 JWT 的 `jti`，登出后复用原 token 会返回 `401`。
- 配置接口以及用户、存储资源、项目、扩容、备份删除/回滚等高风险写操作新增超级管理员依赖，超级管理员来源为 `SUPER_ADMIN_USERNAMES`。
- 邮件模板和任务默认值移除历史产品名、内部域名和个人邮箱；默认站点链接使用本地入口，扩容流程链接未配置时为空。
- NetApp/Isilon 手工集成检查脚本移动到 `backend/scripts/manual_*_check.py`，避免被单元测试收集。
- 主库和 QuestDB 连接池默认值改为保守配置，并支持 `DISKPULSE_DB_*`、`DISKPULSE_QUESTDB_*` 环境变量覆盖。
- Isilon 会话 cookie/CSRF 缓存默认关闭，仅 `DISKPULSE_ISILON_SESSION_CACHE=true` 时启用。
- 请求级数据库会话在异常路径执行 rollback 后再关闭。
- 新增 `docs/standards/domain-terminology.md`，并修正前端标准中的真实样式入口路径。

### 验证状态

- `.\.venv\Scripts\python.exe -m unittest backend.test.test_security_regressions backend.test.test_auth_api`：通过，15 个测试。
- `.\.venv\Scripts\python.exe -m unittest discover -s backend\test -p "test_*.py"`：通过，28 个测试。
- `.\.venv\Scripts\python.exe -m compileall -q backend`：通过。
- 静态扫描确认旧内部域名、个人邮箱、硬编码高连接池、`verify=False` 和 `disable_warnings` 不再存在于后端生产代码；`.dict()` 残留仅为测试中的 `unittest.mock.patch.dict`。

### 风险与后续

- 真实 NetApp/Isilon/LDAP/QuestDB 环境未做端到端连通性验证；TLS 默认开启后，自签名环境需要配置可信 CA 或显式受控降级。
- JWT 撤销列表当前为进程内内存状态；多实例部署需要迁移到 Redis 或数据库等共享存储。
- 未配置 `mail_to` 时，历史默认个人收件人已移除，相关告警邮件会缺少默认收件人并需要部署侧显式配置。
## 2026-06-30：前端体验、可访问性与性能拆包

### 主题

落实前端审查计划，围绕 DiskPulse 管理后台的设计系统、公共组件可访问性、图表加载、页面文案和构建拆包做聚焦改造。

### 已完成

- 新增前端审查合同测试，覆盖应用壳折叠按钮、主题切换、筛选网格、表格错误态/密度、路由术语、ECharts 入口和 Vite 拆包。
- 应用壳侧栏折叠控件改为语义化按钮，补充 `aria-expanded`、`aria-controls`、`aria-label` 和 `focus-visible`。
- `ThemeSwitch` 补充 `aria-label`、`aria-pressed`，恢复 `prefers-reduced-motion` 判断，不再因浏览器不支持 View Transition 输出错误日志。
- `GridContainer`、`QueryForm`、`DataTable` 增强响应式和状态表达，表格支持统一错误态与 `compact` 密度。
- 图表组件改为通过 `frontend/src/lib/echarts.js` 懒加载 ECharts，并复用 `useEchartsChart` 管理初始化、resize 和销毁。
- 概览页、实时详情页新增页面标题、数据范围或最近刷新信息。
- 路由标题和登录页 fallback 文案按 DiskPulse 存储监控术语统一。
- `vite.config.js` 新增 Vue、Element Plus、ECharts 手动拆包配置。
- 新增 `docs/standards/domain-terminology.md`，并修正前端规范中的实际技术栈、样式入口和组件目录说明。

### 验证状态

- `cd frontend && npx vitest run test/unit/frontend-audit-contract.test.js test/unit/frontend-audit-static.test.js test/unit/router/routes.test.js --coverage.enabled=false`：通过。
- `cd frontend && npm run lint`：通过。
- `cd frontend && npm test`：通过，`25` 个测试文件、`121` 个测试。
- `cd frontend && npm run test:coverage`：通过，语句覆盖率 `92.43%`、分支覆盖率 `83.22%`、函数覆盖率 `72.58%`、行覆盖率 `92.43%`。
- `cd frontend && npm run build:test`：通过，主入口 `assets/index-757e3052.js` 为 `31.67 kB`、gzip `8.43 kB`；`echarts`、`element-plus`、`vue-vendor` 和通用 `vendor` 已拆分为独立 chunk。
- Playwright 浏览器烟测：`http://127.0.0.1:5173/login` 在 `375px`、`768px`、`1440px` 视口可渲染；`http://127.0.0.1:5173/` 可渲染概览页骨架和新标题，未接后端时仅出现预期 API `404`。

### 风险与后续

- 未连接真实后端和真实存储设备进行端到端页面验收；本轮验证以组件合同、静态合同、单测、lint 和构建为准。
- 图表视觉细节保持现有图形和数据契约，仅收敛加载入口、生命周期和颜色来源。
- `npm run build:test` 仍保留 Vite 的 `%VITE_APP_TITLE%` 未定义提示和大 vendor chunk 提示；主入口 gzip 已降到规范目标内，后续可继续按业务路由拆页级 chunk。
- 当前改造在独立 worktree `D:\dev\worktrees\DiskPulse\frontend-audit-implementation` 上完成，未回退主工作区既有未提交改动。

## 2026-06-30：NetApp/Isilon 软限额持久化与展示

### 主题

为配额链路新增软限额采集、持久化、API 暴露、导出和前端展示，保留现有硬限额告警口径。

### 已完成

- `StorageUsage`、`Qtree`、`Volume`、`Group`、`Project` 新增 `soft_limit` 和 `soft_use_ratio` 字段。
- `StoragePulseMonitor` 从 NetApp `space.soft_limit` 和 Isilon `thresholds.soft` 获取软限额，linked Isilon 用户继承 default-user 软限额。
- 项目组、项目汇总和 QuestDB 当前态写入同步携带软限额字段；现有告警任务仍按硬利用率 `use_ratio`。
- 用户用量、项目组、Qtree、Volume 列表新增软限额/软利用率列，硬限额列文案明确为“硬限额/硬利用率”。
- 存储使用导出新增“软限额”“软使用率”列。
- 软限额字段已纳入单一 initial baseline；功能说明见 `docs/features/storage-quota/overview.md`。

### 验证状态

- `.\.venv\Scripts\python.exe -m unittest backend.test.test_storage_soft_quota`：通过。
- `.\.venv\Scripts\python.exe -m unittest backend.test.test_core_api`：通过。
- `cd frontend && npx vitest run test/unit/utils/quota.test.js --coverage.enabled=false`：通过。
- `cd frontend && npx vitest run test/unit/smoke/surface-regression.test.js --coverage.enabled=false`：通过。

### 风险与后续

- 未连接真实 NetApp/Isilon 设备做端到端采集验证，本次通过 mock quota payload 覆盖字段解析。
- 旧增量 revision 已删除；初始开发数据库统一从空库执行 `000000000001`，不支持从旧链升级。
- `docs/standards/domain-terminology.md` 已在后续安全修复中补齐。

## 2026-06-30：后端核心接口测试与覆盖率门禁

### 主题

后端核心逻辑审查、核心 API 测试补齐，以及初版核心后端 `70%+` 覆盖率门禁。

### 已完成

- 新增 `backend/test/test_core_api.py`，使用 FastAPI `TestClient`、内存 SQLite 和最小模型种子覆盖核心接口。
- 覆盖认证保护下的用户列表、项目详情与重复创建拒绝、存储集群 CRUD 和 realtime envelope。
- 覆盖 aggregate、volume、qtree、group、storage usage、storage alerts、storage backup records、large files 的列表、状态校验、导出和关键失败路径。
- 修复 `storage-usages/export/` 的 PDF/Excel `Content-Type` 互换问题。
- 修复 `large-files/export/` 的 `.xlsx` 导出返回 `application/pdf` 的问题。
- 新增 `.coveragerc`，按本次确认的“核心后端”口径排除外部设备客户端、QuestDB、Celery、迁移和手动脚本。
- 在 `backend/requirements.txt` 中补充 `coverage==7.13.0`，并已安装到本地 `.venv` 进行验证。
- 将 NetApp 和 Isilon 手动验证脚本改为读取环境变量，避免真实设备地址、账号和密码进入代码库，并避免自动测试误触外部设备。
- 新增 `docs/overview/latest-features.md` 并更新 `docs/README.md` 索引。

### 验证状态

- `.\.venv\Scripts\python.exe -m unittest backend.test.test_core_api`：通过。
- `.\.venv\Scripts\python.exe -m unittest discover -s backend\test -p "test_*.py"`：通过，14 个测试。
- `.\.venv\Scripts\python.exe -m coverage run -m unittest discover -s backend\test -p "test_*.py"; .\.venv\Scripts\python.exe -m coverage report`：通过，核心后端覆盖率 `73%`。

### 风险与后续

- 覆盖率口径为初版核心后端 `70%+`，未把外部设备客户端、QuestDB、Celery worker、迁移脚本和手动探测脚本纳入门禁。
- 部分 CRUD 和 router 仍输出 Pydantic v2 `dict()` 弃用告警，当前不影响测试通过，后续可单独改为 `model_dump()`。
- `docs/standards/domain-terminology.md` 已在后续安全修复中补齐。
- 当前工作区仍存在与本任务无关的未跟踪前端测试文件，本次未纳入也未回退。

## 2026-06-30：前端清理、结构整理与测试补齐

### 主题

前端冗余代码清理、中度结构整理，以及基于 `Vitest` 的测试体系补齐。

### 已完成

- 删除未接入当前前端入口或路由的历史残留目录：`frontend/src/pages_backup/**`、`frontend/src/pages/storage/**`。
- 删除空文件 `frontend/src/components/form/FormDialog.vue`，并清理未被当前路由使用的重复页面与无效工具文件。
- 抽取共享逻辑到 `frontend/src/utils/time-range.js` 与 `frontend/src/router/support/accessibility.js`，同步收敛重复的查询、时间范围和路由可访问性处理。
- 继续抽取选择器共享逻辑到 `frontend/src/composables/select-model.js`，统一 `modelValue` 归一化、`v-model` 发射和单选/多选值展开处理。
- 将 `ProjectSelect`、`AggregateSelect`、`StorageClusterSelect`、`VolumeSelect`、`GroupSelect`、`QtreeSelect`、`StorageUsageSelect`、`AccountSelect`、`HostsSelect`、`RdUserSelect`、`MailSelect`、`UserMail` 的重复同步状态机改为复用公共 composable，并删除失效的默认回填残留代码。
- 清理明显影响可读性的无用 `import`、调试输出与重复 helper，保持现有页面路径和路由契约不变。
- 在 `frontend/package.json` 中新增 `npm test`、`npm run test:coverage`、`npm run test:watch` 脚本。
- 新增 `frontend/vitest.config.js`、`frontend/test/setup.js`、`frontend/test/helpers/mount.js` 以及覆盖 `utils`、`api`、`composables`、`stores`、`router` 和活跃页面 smoke 的测试用例。
- 新增针对高函数缺口区域的聚焦测试，包括路由懒加载、基础 API 包装、表单对话框事件链和表单选择器搜索/回填行为测试。

### 验证状态

- `cd frontend && npm test`：通过。
- `cd frontend && npm run test:coverage`：通过。
- `cd frontend && npm run build:test`：通过。
- `frontend/src` 当前全局覆盖率结果：
  - `statements`: `91.90%`
  - `branches`: `84.31%`
  - `lines`: `91.90%`
  - `functions`: `71.23%`

### 风险与后续

- 本轮已满足初版全局 `70%+` 覆盖率目标；剩余函数缺口主要集中在图表组件、少量列表页事件处理和部分未细测的表单选择器上，后续可继续按覆盖率报告定点补强。
- 当前 `vitest` 执行期间仍会输出 Sass legacy JS API 弃用告警，不影响本轮测试通过，但后续升级 Sass/Vite 链路时需要单独消化。
- `npm run build:test` 已通过，但打包结果仍提示存在 `500 kB+` chunk，后续如继续整理前端结构，建议结合路由懒加载和手动拆包一起处理。
- 当前工作区仍存在与本任务无关的后端和仓库级未提交改动，本次未回退也未纳入前端交付范围。
- 前端测试说明已新增到 `docs/guides/frontend-testing-guide.md`，后续新增页面或公共模块时应同步补测试。

## 主题

后端 LDAP 登录登出认证、JWT 保护业务 API 和前端登录流程对齐。

## 已完成

- 新增 LDAP directory 查询、LDAP filter 转义、多 user base 搜索和 STARTTLS-before-bind 行为。
- 新增 HMAC-SHA256 JWT 签发与校验；当前安全契约要求 `Authorization: Bearer <token>`。
- 新增 `/storage-pulse/api/users/login`、`/users/logout`、`/users/current/profile`，保持前端 `{ result: ... }` 契约。
- `/storage-pulse/api/**` 除登录和 `OPTIONS` 外默认要求有效 JWT；登出接口同样要求有效 Bearer token。
- 移除前端登录页本地 `superadmin` 绕过，所有账号统一走后端登录接口。
- 新增后端认证测试和前端登录流程测试。
- 同步认证文档、配置示例和依赖声明。

## 未包含

- 未新增数据库字段或 Alembic migration，继续复用 `users.rd_username`。
- 未接入真实 LDAP 做端到端连通性验证；真实环境需配置 `LDAP_SERVER_URL`、bind 凭据、user bases 和 TLS 参数。
- 未处理当前工作区中与本任务无关的既有未提交改动。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest backend.test.test_auth_ldap backend.test.test_auth_api
.\.venv\Scripts\python.exe -m unittest discover backend/test
.\.venv\Scripts\python.exe -m compileall -q backend
.\.venv\Scripts\python.exe -m pip check
cd frontend
npx vitest run test/unit/auth-login.test.js --coverage.enabled=false
npm test -- --coverage.enabled=false
```

## 2026-07-14：修复 QuestDB 软限额指标写入失败

### 已完成

- 新增 `000000000002_add_soft_quota_metrics` 前向迁移，为 Volume、Qtree、Project、Group 和用户用量历史表补充 `soft_limit`、`soft_use_ratio`。
- 保留已执行的 `000000000001_initial_schema` 不变，避免已有环境出现迁移校验和冲突。
- Aggregate 和 StorageCluster 继续使用物理容量口径，不再向 Aggregate 指标写入软限额字段。
- 增加迁移链、已有 `0001` 环境升级和 Aggregate 写入参数回归测试。

### 验证状态

- `cd backend && ..\.venv\Scripts\python.exe -m pytest test\test_questdb_migrations.py test\test_storage_soft_quota.py -q`：通过，`17 passed`。
- `cd backend && ..\.venv\Scripts\python.exe -m pytest test\test_questdb_migrations.py test\test_storage_soft_quota.py test\test_storage_collection_trigger.py -q`：通过，`23 passed`。
- `.\.venv\Scripts\python.exe -m compileall -q backend` 和 `.\.venv\Scripts\python.exe -m pip check`：通过。

### 部署动作与风险

- 当前开发实例已显示 revision `000000000002`，幂等 upgrade 返回 `up to date`；实际列检查确认五张配额历史表包含两个软限额列，Aggregate 不包含。
- 其他环境更新代码后需在 `backend` 目录执行 `..\.venv\Scripts\python.exe -m questdb.migrate upgrade`，再重启 Celery worker。
- 尚未重新触发真实 NetApp 采集；需要在 worker 加载新代码后观察一次 Volume、Aggregate 和 Cluster 三类写入日志。

## 2026-07-14：修复 NetApp Qtree API 400

### 已完成

- 从 `storage/qtrees` 的 `fields` 参数中移除当前 ONTAP 不支持的 `oplocks`。
- 保留现有缺省行为：响应不含 `oplocks` 时，Qtree 的该展示字段按 `False` 处理。
- 增加请求字段回归测试。

### 验证状态

- `cd backend && ..\.venv\Scripts\python.exe -m pytest test\test_security_regressions.py -q`：通过，`13 passed`。
- 使用修改后的客户端只读访问北京 NetApp：成功返回 `82` 条 Qtree。

### 风险

- 该历史记录中的全局 `storage.tls_verify` 已被逐集群字段取代；`tls_verify=false` 的 HTTPS 集群仍会输出预期的 `InsecureRequestWarning`。
- Celery worker 需重启后才能加载本次客户端修改。
## 2026-07-15：统一存储集群分析页筛选与图表布局

### 已完成

- 将时间范围和导出操作移入分析页签内容区；容量趋势、性能分析和故障分析保留筛选入口，存储分布不展示时间筛选栏。
- 时间范围字段扩宽并补全日期时间占位文案，避免输入内容被截断。
- 容量趋势与存储分布主图统一为 `520px`；存储分布复用 Element Plus 全局加载遮罩。
- 存储分布不展示筛选和导出栏，避免时间范围造成错误的数据范围暗示。

### 验证状态

- `cd frontend && npx vitest run test/unit/pages/storage-cluster-health-analytics.test.js --coverage.enabled=false`：通过，`9 passed`。
- `cd frontend && npm run build:prod`：通过。
- Playwright `1440×900` 浏览器检查：筛选栏位于 `.el-tabs__content` 内，存储分布绘图区最小高度为 `520px`；延迟请求期间标准加载遮罩完整覆盖 `1097.6×520px` 绘图区且 `aria-busy=true`。后续回归测试确认切换到存储分布时筛选栏隐藏。

### 风险

- 本地浏览器未登录，后端请求返回预期的 `401`；尚未使用真实数据复验图表内容和导出下载。

## 2026-07-15：Isilon Session 缓存改为集群级配置

### 已完成

- `storage_clusters` 新增 Session 缓存模式与本地文件路径，支持 `none`、`file`、`redis`；已有集群迁移后默认 `none`。
- Isilon 管理表单按缓存模式条件展示本地文件路径；NetApp 不展示并清空 Isilon 专属字段。
- 文件缓存使用可配置路径和原子替换，Redis 复用全局连接配置并使用独立 DB/OneFS Session TTL。
- 未配置缓存或缓存写入失败时，采集结束调用 OneFS logout 安全释放 Session；日志不输出 Cookie、CSRF Token 或密码。

### 验证状态

- RED：后端 `8 failed, 6 passed`，前端 `1 failed, 12 passed`，失败均由缺少缓存配置契约引起。
- GREEN：后端聚焦测试扩展后 `66 passed`；前端表单测试 `13 passed`；生产构建、Python compileall、依赖检查和 Redis 测试库真实读写通过。

### 部署动作与风险

- 本地测试环境 PostgreSQL 已执行 `alembic upgrade head` 到 `000000000005`；其他环境升级后需重启后端与 Celery worker。
- 本地文件和 Redis 中保存的是有效 OneFS 认证材料，部署环境必须限制缓存文件 ACL 与 Redis 网络访问。
- OneFS 真机 Redis Session 复用尚未验收；当时出现的 PAPI 登录 `403` 后续已定位为 NIS 人员账号触发身份解析后有效角色丢失，见下一节。

## 2026-07-15：隔离 Isilon 采集账号身份并恢复 LDAP 用户关联

### 已完成

- 确认 403 只在 NIS 人员账号触发身份解析后出现，安全注销、角色 UID 绑定和并发 Session 数均不是根因。
- 改用加入 `DiskPulseMonitor` 只读角色的 OneFS 本地服务账号，配额恢复 `resolve_names=true`，用解析出的用户名关联已同步的 LDAP 用户。
- 保留 `persona.id=UID:<数字>` 回退和未知 persona 跳过逻辑；不新增第二套 LDAP 同步实现。

### 验证状态

- RED：本地服务账号验收通过后，请求测试仍观察到默认 `resolve_names=false`，用例失败。
- GREEN：默认请求恢复 `resolve_names=true`；资源映射、软限额、Session 生命周期、采集触发和安全回归合计 `55 passed`，`compileall` 与 `pip check` 通过。
- 真机验证：本地服务账号完成 `201 → 2270 条 resolve_names=true 配额 → 安全注销 → 201`；第二个 Session 状态为 `200`，性能接口返回 1 条记录。
- 用户关联验证：`UID:104407` 解析到目录用户名，LDAP 精确查询返回 1 条记录并包含姓名、邮箱；目标目录未提供 department 属性。

### 部署动作与风险

- Celery worker 必须重启才能加载新默认参数。
- 其他 Isilon 集群若仍使用 NIS/LDAP 人员账号，应先切换为 OneFS 本地只读服务账号；未知 persona 类型继续安全跳过。

## 2026-07-15：补充 Isilon 采集账号帮助

### 已完成

- 存储集群表单仅在选择 Isilon 时显示“查看账号创建与最小权限配置”入口。
- 帮助弹窗说明必须使用 System Zone 的 OneFS 本地服务账号，并列出登录、集群、SmartPools、Quota、Statistics、Event 和系统时间只读权限。
- 弹窗和存储集群文档提供同一套 root 创建用户、创建角色、授权及验证命令，并提示 HTTPS、安全注销和 Celery Worker 重启要求。

### 验证状态

- RED：选择 Isilon 后帮助入口不存在，新增组件用例失败。
- GREEN：存储集群表单组件 `14 passed`；目标组件覆盖率 statements/lines `100%`、branches `98.43%`、functions `80%`。帮助入口仅对 Isilon 显示，弹窗包含账号名、创建命令和关键权限；改动文件 ESLint `0 errors`，生产构建通过。

## 2026-07-16：性能分析条数与多指标筛选

### 已完成

- 性能分析新增 10、20、50、100 条筛选，默认 10 条，后端 `limit` 上限同步扩展到 100。
- 性能指标支持多选，默认 P95；可展示平均/最大/读/写延迟、IOPS 和吞吐量，不同单位独立成图，表格列跟随所选指标。
- 分析查询聚合 QuestDB 既有统一字段；PowerScale workload 的操作数和收发字节映射到 IOPS、吞吐量，NetApp 继续读取 Volume `metric` 的嵌套总值。

### 验证状态

- RED：后端新增契约 `3 failed, 1 passed`，前端页面 `2 failed, 9 passed`；失败点均为缺少本次行为。
- GREEN：后端新增契约 `4 passed`；存储健康整文件（排除已记录的迁移定位失败）`94 passed, 1 deselected`；前端页面 `11 passed`，目标页面覆盖率 statements/lines `96.18%`、branches `74.54%`、functions `82.75%`；定向 ESLint `0 errors`，生产构建与 Python `compileall` 通过。

### 风险

- 尚未用真实 NetApp、PowerScale 和 QuestDB 数据复验多指标数值与页面布局；部署后需重启 Celery worker，等待新采集样本再验收 IOPS/吞吐量。
- 存储健康测试文件的既有迁移定位用例仍有 1 个已记录失败，见 `docs/tracking/error-log.md`；本次未修改迁移链。

## 2026-07-16：存储性能与事件采集专题文档

### 已完成

- 新增性能/事件采集设计、NetApp/PowerScale 与 DiskPulse API 契约、部署排障与真机验收三篇文档。
- 文档串联近期已完成的 path workload、单位转换、Session、EMS/OneFS 事件解析、统一指标、页面筛选和已知排障结论，并引用 Dell/NetApp 官方接口资料。
- 更新存储集群专题和根文档索引。

### 验证状态

- 文档内容已依据当前采集、分析、路由实现和 `docs/tracking/error-log.md` 的已记录真机排障结果复核；相对 Markdown 链接与 `git diff --check` 均通过。

### 风险

- 厂商 API 的实际字段和权限会随 OneFS/ONTAP 版本、license、workload 配置变化；文档中的真机结论只适用于已记录环境，其他集群仍需按验收清单验证。

## 2026-07-16：修复配额调整记录误显示为使用率告警

### 已完成

- 告警列表识别 `quota_adjustment`，显示后端保存的配额调整描述。
- 配额调整记录的事件类型、限额口径、级别、阈值和触发值显示 `-`，不再把容量字段解释为告警百分比。
- 保持真实容量告警的使用率计算和显示逻辑不变，无需迁移历史数据。

### 验证状态

- RED：告警页聚焦测试 `8 passed, 1 failed`，确认页面缺少配额调整分流。
- GREEN：告警页聚焦测试 `9 passed`；目标页面 ESLint `0 errors`；生产构建通过。

### 风险

- 未连接运行中的前后端做浏览器截图复验；修复仅调整前端展示，不修改后端存量记录。

## 2026-07-16：配额调整接入飞书通知

### 已完成

- 项目组配额调整成功后通知负责人，用户目录配额调整成功后通知目录用户；收件人继续遵守现有 `debug`、全局抄送和超级管理员规则。
- `quota_adjustment` 记录保存飞书标题、正文、收件人和投递状态，数据库提交后复用 `deliver_storage_alert_task` 异步发送及重试。
- 飞书入队失败只记录错误并保留待投递记录，不回滚已经成功的设备配额和数据库更新；原邮件通知保持不变。

### 验证状态

- RED：配额调整聚焦测试 `2 failed, 13 passed`，确认服务没有飞书配置和入队边界。
- GREEN：配额调整与飞书投递聚焦测试合计 `45 passed`，覆盖项目组、用户目录、正文、收件人、重试契约和 Broker 入队异常。

### 风险

- 未连接真实 Redis/Celery 和飞书通知服务验证实际送达；当前环境已有飞书地址 TCP 不可达记录，部署前需先恢复通知服务连通性并重启 API、Celery worker 和 Celery beat。

## 2026-07-17：合并前端审计与配额响应式分支

### 已完成

- 将 `codex/frontend-audit-implementation` 通过合并提交 `8146e94` 纳入 `main`，保留共享 ECharts 生命周期、可访问性、主题和构建分包改进，并与当前 Dashboard、存储术语及路由实现完成冲突整合。
- 将 `codex/quota-progress-responsive` 通过合并提交 `7d01ae5` 纳入 `main`，统一列表响应式列、固定使用率与操作列宽，并使用全局告警阈值映射四档使用率颜色。
- 调整合并后的旧覆盖测试：组件挂载注入 Pinia，图表用例等待异步初始化并按共享生命周期断言；告警回归测试只收集其声明检查的弃用告警。
- 确认两个分支 tip 均为 `main` 祖先后，移除两个独立 worktree，并使用安全删除删除对应本地分支；本地及远端均无其他未合入 `main` 的分支。

### 验证状态

- 后端全量测试 `370 passed`。
- 前端全量测试与覆盖率测试均为 `56 files / 341 passed`，覆盖率 statements `98.32%`、branches `89.51%`、functions `83.72%`；ESLint 与生产构建通过。
- 两个 worktree 删除前均无未提交改动，`git diff --check` 通过。

### 风险

- 本次仅完成本地 `main` 合并与清理，未推送远端。
- 保留既有两个安全 stash，未自动恢复或删除，避免覆盖历史现场。

## 2026-07-17：统一限额与存储类型标签

### 已完成

- 容量池、存储空间、Qtree（NetApp）、项目组、项目和用户目录列表将空硬限额文案统一为“无硬限额”，软限额继续显示“无软限额”。
- 无硬限额使用 `danger`，无软限额使用 `warning`；用户目录存储类型使用 `success`，项目及项目组相关视图使用 `info`，移除这些标签对共享紫色样式类的依赖。
- 配额格式化默认文案和离职用户周报邮件同步更新，静态标签契约测试改为验证语义类型。

### 验证状态

- 标签、配额、响应式列和页面烟测聚焦测试 `4 files / 90 passed`。
- 前端全量覆盖率测试 `56 files / 341 passed`；受影响前端文件 ESLint、生产构建与 `git diff --check` 通过。

### 风险

- 未在登录态浏览器中逐页检查标签的最终视觉效果。

## 2026-07-17：LDAP 周期同步与用户存储小时快照

### 主题

在不改变人工 LDAP 同步和每分钟全量存储采集的前提下，增加每 8 小时 LDAP 自动同步，以及每小时从 PostgreSQL 当前 `StorageUsage` 生成 QuestDB 用户维度时序样本。

### 实现状态

- 状态：本地实现完成。RED 测试提交为 `b82d94e`（周期调度、LDAP 任务、用户聚合和 QuestDB migration 契约）与 `57a9d29`（任务可观测失败路径）；GREEN 实现提交为 `9bc840d`。
- LDAP 自动任务已复用 `usersService.sync_ldap_users`，使用独立 PostgreSQL 会话和 Redis 非阻塞锁，保持原有提交、回滚和失败行为；Beat/Worker 启动时不立即执行，人工同步接口继续保留。
- 现有 `storages_schedule_fetching_task` 的每 60 秒全量采集保持不变。用户统计任务每小时整点读取 PostgreSQL 当前值，按非空 `user_id` 汇总 `limit`、`soft_limit`、`used`、`file_used`，基于汇总值计算两类使用率，并以同一采样时间写入 QuestDB `user_storage_usages`。
- PostgreSQL 无有效来源行时成功返回 `count=0`；QuestDB 写入或提交失败时回滚并让 Celery 任务失败。此次未新增前端或 API。
- QuestDB 新增前向 revision `000000000004_user_storage_usages.sql`，当前 schema head 为 `000000000004`。

### 验证状态

- 状态：本地自动化验证完成。
- RED 阶段确认新增测试在缺少实现时按预期失败；GREEN 后执行以下聚焦测试，共 `64 passed`：

```powershell
.\.venv\Scripts\python.exe -m pytest backend\test\test_scheduled_user_tasks.py backend\test\test_questdb_migrations.py backend\test\test_user_management_ldap_sync.py backend\test\test_celery_app_contract.py backend\test\test_storage_collection_trigger.py -q
```

- 全量后端覆盖率验证：先执行 `.\.venv\Scripts\python.exe -m coverage run -m pytest backend\test -q`，再执行 `.\.venv\Scripts\python.exe -m coverage report`；结果为 `386 passed`，`TOTAL 91%`，满足 `.coveragerc` 的 `85%` 门禁。
- `.\.venv\Scripts\python.exe -m compileall -q backend`：通过。
- `git diff --check`：通过。

### 风险与部署边界

- 当前只确认代码和本地自动化测试通过，尚未连接真实 LDAP、Redis、PostgreSQL、QuestDB，也未验证部署环境中的 Celery Beat/Worker 实际投递、锁竞争和周期执行。
- 部署时仍需先将 QuestDB 升级到 `000000000004`，再重启或启用新增 Beat 调度；否则小时任务会因目标表不存在而失败。
- 小时聚合读取执行时 PostgreSQL 已提交的当前值，不保证与某个存储设备采集轮次严格绑定；同一 `updated_at` 表示聚合采样时间。

## 2026-07-17：存储集群与存储类型展示统一

### 已完成

- 用户目录、项目组、项目、容量池、存储空间、Qtree 和存储集群管理列表统一使用独立的“存储集群”“存储类型”列。
- 存储集群名称显示为普通文本，存储类型复用绿色成功标签；空值统一显示 `-`。
- 项目列表接口新增当前页关联集群摘要，去重并稳定排序；多集群项目的名称和类型保持逐行对应。

### 验证状态

- 后端项目集群摘要、项目 CRUD 和核心 API 聚焦测试 `24 passed`。
- 前端展示一致性、响应式列、标签颜色及相关页面回归测试 `8 files / 62 passed`；受影响前端文件 ESLint 通过。
- 前端全量测试与覆盖率测试均为 `57 files / 351 passed`，覆盖率 statements `98.33%`、branches `89.52%`、functions `83.72%`；完整 ESLint 和生产构建通过。

### 风险

- 登录态浏览器逐页视觉检查未完成：本地 `http://localhost:52341/` 当前拒绝连接；自动化测试不能替代最终视觉验收。
- 后端工作区同时存在另一任务未提交的 Celery/QuestDB 改动，本次不运行会混入该任务代码的后端全量测试。

## 2026-07-17：应用页脚固定到工作区底部

### 已完成

- 在应用头部下方保留“侧栏 + 工作区”横向结构，将右侧工作区调整为“主内容 + 页脚”纵向结构。
- `AppFooter` 从业务内容 `ElScrollbar` 中移出并固定占用底部 `40px`；主内容使用剩余高度独立滚动。
- 页脚宽度随工作区自适应，侧栏展开、折叠或隐藏时不需要维护固定定位偏移。
- 保留原版权文字、动态年份、居中、主题颜色和上边框，不修改路由、业务页面或后端。

### 验证状态

- RED：应用壳聚焦测试 `2 failed, 4 passed`，分别复现默认高度仍为 `60px`、缺少独立工作区且页脚位于滚动容器内。
- GREEN：同一聚焦测试 `6 passed`。
- 前端全量覆盖率测试 `60 files / 359 passed`；覆盖率 statements `98.30%`、branches `88.74%`、functions `84.17%`、lines `98.30%`。
- 目标 ESLint 通过，结果为 `0 errors, 2 warnings`；两条 warning 均为测试文件既有的 `vue/one-component-per-file`。
- 生产构建通过，仅保留既有的大分块 warning；`git diff --check` 通过。

### 风险

- 按用户后续要求跳过完整浏览器验证，未执行缩短视口后的内容滚动稳定性和最后一段内容可见性验收；自动化测试只锁定 DOM 结构与高度合同。
- 既有窄屏固定侧栏溢出不属于本次页脚修复范围。
