# 前端设计与开发规范

本规范约束 DiskPulse 的 `frontend/` 改动。目标是让存储监控管理后台保持高信息密度、统一交互和可验证的权限边界；遇到冲突时，以本规范的“必须”规则、现有共享组件和自动化测试为准。

## 1. 开工边界

- 开始前**必须**阅读本文、[文档规范](../documentation/documentation-standard.md)、[Git 提交规范](../git/git-commit-standard.md)、[开发阅读矩阵](../documentation/development-reading-guide.md)和 `frontend/src/styles/style.scss`。
- 前端任务默认只改 `frontend/` 与相关 `docs/`；只有需求明确涉及接口、权限或数据契约时才联动 `backend/`。
- 功能、接口、配置、权限、测试入口或用户可见行为变更时，**必须**同步事实文档和本会话 `docs/tracking/sessions/<session-id>/delivery.md`；可复现错误按[开发跟踪索引](../../tracking/README.md)分类记录，计划不能写成已完成。
- 先检索同类页面和共享组件，再改动。禁止根据单张截图复制一套局部样式；跨页问题优先修复共享组件、token、布局或测试门禁。

## 2. 不可例外的 UI 规则

### 2.1 信息层级与布局

- DiskPulse 是专业存储监控管理后台。首屏**必须**直接呈现查询、数据、状态和可执行操作；禁止营销页、装饰性 Hero、大图和只重复页面名称的说明区。
- **禁止在标题后设置描述性副标题。**页面、详情、页签、弹窗和登录页只保留必要标题与操作入口。术语解释、风险和限制分别放入字段标签、Tooltip、帮助入口或就近提示；错误提示、空态和图表数据状态不属于副标题。
- 外层留白只由 `AppLayout.vue` 的内容容器负责。页面根节点、通用布局、查询栏和数据卡片不得重复叠加等价 `padding`；只使用现有 `--spacing-*` token，不以临时像素值推开内容。
- 页面级禁止横向滚动。宽表格只允许在表格容器内滚动；窄屏优先隐藏低频列、回落单列或折叠次要筛选条件。
- 头像、姓名、角色和时间等身份行**必须**使用显式 flex 对齐：单行垂直居中，多行消息以首行基线对齐，头像不可压缩。禁止负 margin、相对定位或修改行高来碰运气修正偏移。
- 用户头像统一复用 `components/data/UserAvatar.vue`，与顶栏共用数据来源和后备策略；列表、消息和选择器不得复制头像颜色、边框或图标逻辑。

### 2.2 共享组件与视觉语义

下列场景**必须**复用对应组件；只有静态、无查询、无加载、无分页的少量键值信息可例外，并在代码注释中说明原因。

| 场景 | 必用组件/约束 |
| --- | --- |
| 查询、筛选、搜索、重置、导出 | `components/form/QueryForm.vue`；搜索在最右且为蓝色主操作，重置为中性操作，导出为绿色。 |
| 查询、分页、加载、空态或列配置的数据表 | `components/data/DataTable.vue`，包括详情页 Tab 内的成员、审计和资源表。 |
| 表格行操作与表头“添加” | `components/basic/TableActionButton.vue`；固定 `size="small"` 与 `plain`。新增/启用/同步/回滚为绿色，详情为灰色，编辑/测试为蓝色，删除/移除为红色。 |
| 可访问的资源名称或关联资源 | `components/basic/AccessibleResourceLink.vue`；仅当目标路由、关联 ID 与当前用户权限均成立时显示链接，否则显示普通文本。 |

- 操作列最多直接展示两个操作，其余收入“更多”；操作列**必须**右侧固定、右对齐、显式宽度并复用 `.list-row-actions`。禁止在操作列直接使用 `ElButton`、`ElLink` 或 `link` 形态绕过 `TableActionButton`。
- 资源链接必须使用轻量样式：`font-weight: 400` 和低饱和蓝色；禁止 `ElLink type="primary"`、加粗或深色链接造成与表格正文不一致。
- `ElTag` 只表达状态、类型或筛选选中态，不能充当操作按钮，也不能使用与全局状态语义冲突的自定义高饱和色。
- 颜色、阴影、边框和主题值先定义在 `frontend/src/styles/variables.scss`，再在共享样式或组件中引用。业务页面不得散落新增色值；图表使用 chart token，不挪用按钮或 Tag 的状态色。
- 自研交互控件**必须**具备键盘路径、`focus-visible` 和 ARIA；`SearchSelect` 保持 combobox/listbox 语义。

### 2.3 详情、权限与操作闭环

- 从列表读取同一上下文的一条记录时，默认使用右侧详情抽屉。审计、事件等同类详情**必须**复用相同的抽屉结构、字段节奏、加载、空态和关闭行为；独立导航、可分享 URL、复杂子页面或编辑工作流才建立详情路由。
- 菜单、页面入口、按钮和链接**必须同时**遵守权限边界。前端隐藏仅改善体验，不能替代后端授权；管理员与超级管理员的差异以现有角色/能力字段表达，并覆盖允许与拒绝两类测试。
- 写操作必须形成完整闭环：可见入口能打开表单或抽屉；提交中防重复；成功后提示并刷新当前数据；失败后给出可理解错误。禁止“按钮可见但无响应”、前后端权限不一致或 Mock 可操作而真实环境不可操作。
- 文案使用术语表中的中文名称，不暴露设计说明、实现说明或 prompt 痕迹。诊断先给出易懂结论和证据状态，再展示设备来源、指标与原始标识；不得直接把歧义内部词作为用户主文案。

## 3. 数据、监控与 Mock

- 默认请求真实后端 API；Mock 仅通过 `VITE_USE_MOCKS=true` 或 `pnpm mock` 启用。响应必须保留真实 `data`、`meta`、`traceId` envelope 和字段命名，且不得包含真实用户信息、密钥、token 或敏感地址。
- 容量字段必须优先展示 API 返回的 `capacity.{field}`，曲线按 `data_unit` 标注；不得硬编码容量后缀或重复换算。详细规则见[容量单位 API 契约](../backend/capacity-unit-contract.md)。
- Mock **必须**覆盖页面每个可见字段、状态和详情区的代表性演示数据，包括诊断说明、证据摘要、关联资源和写操作后的状态变化；不得用空壳数据掩盖缺字段问题。
- 专用资源监控页优先展示该资源直接相关的容量和性能。容量趋势为独立主图；多指标性能可多选，所选每项各自成图，单项无数据不能阻断其他图。
- 图表保持紧凑：标题、时间范围、指标选择和数据状态相邻；禁止为装饰增大最小高度、`grid.top` 或标题下空白。
- 页面组件继续懒加载；ECharts 只能经 `frontend/src/lib/echarts.js` 懒加载。主入口 gzip 目标不超过 `100KB`，超出时拆包并说明原因。
- “主详情 + 页签”页面首屏只请求主详情和当前页签；其余页签首次访问再加载。数据集有界时优先一次加载并在前端筛选、分页，数据量大时允许后端分页并说明理由。

## 4. 结构与实现位置

- 技术栈为 Vue 3、Vite、Vue Router、Pinia、Element Plus、UnoCSS、ECharts 和 SCSS；全局入口为 `frontend/src/styles/style.scss`，变量为 `frontend/src/styles/variables.scss`。
- 通用组件放 `frontend/src/components/`，基础/数据/表单组件分别放 `basic/`、`data/`、`form/`；复用业务流程放 `services/` 或 `composables/`，不把鉴权、校验、序列化和任务状态堆进大视图。
- Admin API 按资源域放 `frontend/src/api/admin/`，不得恢复聚合 `frontend/src/api/admin.js`；路由定义放 `frontend/src/router/routes.js`，可访问性判断复用 `frontend/src/router/support/accessibility.js`，页面保持懒加载。
- 表单校验、payload、筛选参数、时间转换和响应归一化应就近复用已有模块；出现跨页面重复逻辑时再提取为共享工具，禁止为目录形式而创建空壳抽象。

## 5. 测试、验证与交付

- 修复或新增行为**必须 TDD**：先补失败测试，再实现，再验证。涉及 API、Mock、权限、公共组件、路由、状态、校验或序列化时必须补单测。
- 标题层级、表格操作、资源链接、头像/消息排版、详情抽屉、权限可见性和 Mock 字段变更，测试至少覆盖允许与拒绝权限、默认/空/失败数据、关键交互，以及一项窄屏或长文本场景。
- 静态策略门禁持续检查：禁止标题加描述性副标题、`TableActionButton` 的尺寸/朴素样式/语义色、轻量资源链接的字重与颜色，以及关键 Mock 字段。
- 聚焦验证使用 `cd frontend && pnpm exec vitest run <file> --coverage.enabled=false`；全量测试使用 `pnpm test`；显式覆盖率验证使用 `pnpm run test:coverage`。Vitest 当前对 Statements、Branches、Functions、Lines 均要求不低于 `80%`。
- Dialog、Select、Popover 等 portal 组件测试必须挂载到 `document.body`，并在 `afterEach` 清理 DOM 和 wrapper。临时 Node 脚本按 ESM 语义编写，不假设 `require()` 可用。
- 提交前运行受影响的 Vitest、必要的 `pnpm run lint` / 构建检查和 `git diff --check`；最终说明必须如实列出已验证项、未验证范围、原因与风险。
