# 前端项目规范（AI 快速版）

本规范用于让 AI 快速判断 `frontend/` 改动边界、实现位置和验证范围。

## 1. 开工前

- 涉及前端代码、样式、测试、构建、页面交互或前端文档时，先读本文、`docs/standards/documentation-standard.md`、`docs/standards/domain-terminology.md` 和 `frontend/src/styles/style.scss`。
- 前端任务默认只改 `frontend/` 和相关 `docs/`；除非需求明确联动后端，不改 `backend/`。
- 功能、接口、配置、权限、测试入口或用户可见行为变化，必须同步 `docs/` 和 `docs/tracking/current-release.md`。

## 2. 技术与目录

- 技术栈：Vue 3、Vite、Vue Router、Pinia、Tailwind CSS v4、shadcn-vue、lucide。
- 全局样式入口：`frontend/src/styles/style.scss`；共享变量：`frontend/src/styles/variables.scss`。
- 通用组件放 `frontend/src/components/common/`；表格组件放 `frontend/src/components/tables/`；shadcn 源码组件保留在 `frontend/src/components/ui/`。
- Admin API 按资源域放 `frontend/src/api/admin/`，不得恢复 `frontend/src/api/admin.js` 聚合大文件。
- 路由定义放 `frontend/src/router/routes.js`；守卫放 `frontend/src/router/guards/`；页面组件继续懒加载。
- 表单 schema 放 `frontend/src/validation/`；payload、筛选参数、时间转换和响应归一化放 `frontend/src/serializers/`。
- 复用业务流程放 `frontend/src/services/` 或 `frontend/src/composables/`；不要把鉴权、校验、序列化、任务状态继续堆进大视图。

## 3. UI 与交互

- 本项目是专业回归分析工作台，首屏直接进入可操作界面；不做营销页、落地页、装饰性 hero。
- 全站主品牌统一使用“回归分析平台”或“回归分析工作台”；`AI` 只用于真实存在的 AI 能力域，不把 AI 写成全站主品牌。
- 页面标题和副标题必须直接描述当前页面真实职责、数据范围和操作入口；不得继续使用历史能力名、方案名或没有入口的营销式说法。
- 登录页、应用壳、README 截图说明和页面级 `PageHeader` 文案必须一致表达当前网站定位：回归总览、失败诊断、问题跟踪、项目协作和管理维护。
- 页面优先复用已有公共组件，可以根据需求开发新的组件或者引入安装npm包或者shadcn ui组件。
- 卡片只用于真实信息单元或交互容器；禁止无意义卡片嵌套。
- 桌面端信息展示卡片优先走紧凑密度：默认单层容器内边距使用 `var(--space-md)`（16px）；现有 18px 存量可维持；不要在 `CardHeader/CardContent` 之外再叠一层等价 `padding`，避免头部和图表之间出现双倍留白。
- 指标卡统一使用“左图标 + 右文字栈”的横向信息流；同一组指标卡内不要混用“图标在左、标题在右”和“标题在上、图片在下”两种结构。
- 图表卡统一使用紧凑头部：标题、副标题/时间戳与图表正文之间保持短节奏，优先复用 `.panel__header--compact` 和 `.panel__body--chart` 这类共享结构，不单独在业务组件里追加大块顶部留白。
- 桌面端图表容器以“先信息密度、后视觉呼吸”为准：图表主绘图区应尽量贴近标题区，避免仅为装饰把 `grid.top`、容器最小高度或空白占位拉得过大。
- 同一工作区中的展示卡片要统一媒体方向和标题位置；如果是列表/图表卡，标题始终在卡片顶部，图形内容始终在正文区，不做左右漂移式标题布局。
- 分析工作台这类“页签头 + 内容区”双层结构，页签容器与当前内容区首块之间统一使用 `16px` 纵向间距；间距只能挂在当前激活面板上，不能依赖根容器 `gap` 叠加多个隐藏面板，否则不同 tab 会出现阶梯式留白。
- 全站筛选栏默认不再显示“筛选条件 / 问题筛选 / 任务筛选”这类标题和说明文案；筛选区直接展示字段、主操作和“更多筛选”折叠入口，避免重复占高。
- 全站列表页和详情页筛选栏统一复用 `frontend/src/components/form/QueryForm.vue`；每个筛选项采用“label + 组件”结构，label 位于控件上方并左对齐，使用主文字色、标准字号和半粗字重。
- 主筛选和高级筛选共用同一字段轨道和等宽自适应网格：展开高级筛选后，所有可见条件继续在同一个网格中排列，每行按容器宽度显示 `1–5` 个组件，常规最小列宽为 `220px`，容器不足时允许单列继续收缩；右侧动作区独立占列，且不得通过隐藏 DOM 占位模拟对齐。普通输入占一个标准列，`.query-form-field--wide` 不得改变宽度；需要完整展示起止年月日时分秒的时间范围使用 `.query-form-field--date-range` 跨两个标准列，手机端回落单列。复杂页面通过 `advanced`、`advancedCount` 和 `active-filters` 管理次要条件。
- 查询栏动作区按“辅助操作、更多筛选、重置、导出、搜索”排列；导出使用绿色成功态并与蓝色搜索按钮相邻，搜索固定为最右主操作。页面继续通过 `actions`、`exportExcel` 插槽扩展动作，不得自行复制另一套筛选容器。
- 页面级禁止横向滚动；宽表格只能在 `.table-wrap` 等容器内横向滚动。
- 列表或表格的行操作最多两个时直接展示；超过两个时保留一个高频操作，其余收入“更多”，触发按钮计入两个直显操作之一。操作列统一固定宽度、右对齐、单行展示，并复用全局 `.list-row-actions` 样式；危险菜单项使用 `.list-row-actions__danger`。该规则不处理筛选栏、表头、页面工具栏、卡片操作或弹窗底部按钮。
- 颜色、阴影、边框、主题值先进入 `tokens.css`，再由 `style.css` 或组件引用；业务组件不要散落新增颜色值。
- 表单输入优先用 shadcn `Input`、`Textarea`、`Select`；创建/编辑弹窗字段标签统一用 `FormFieldLabel`。
- `Button` 图标使用 `data-icon="inline-start"` 或 `data-icon="inline-end"`；状态徽标优先用 `Badge` 或已有状态类。
- 自研交互控件必须有键盘路径、`focus-visible` 和 ARIA；`SearchSelect` 必须保持 combobox/listbox 语义。
- 页面文案使用产品语言，不写设计说明、实现说明或 prompt 痕迹。
- 页面文案不得宣传当前未实现或已移除的能力，例如失败签名页、Pareto、失败流向或独立仿真搜索站点。（注：该清单应随版本演进更新，以 docs/tracking/ 为准）

## 4. 数据、Mock 与性能

- 默认调用真实后端 API；Mock 只用于演示和无后端本地开发，通过 `VITE_USE_MOCKS=true` 或 `npm run mock` 开启。
- Mock 响应必须模拟真实 envelope：`data`、`meta`、`traceId`；字段名必须与后端一致。
- Mock 数据不得包含真实用户隐私、真实密钥、生产 token 或敏感内部地址。
- 页面组件必须懒加载；ECharts 只能通过 `frontend/src/lib/echarts.js` 懒加载，D3 只能通过 `frontend/src/lib/d3.js` 懒加载。
- 回归详情这类”主详情 + 子页签集合”页面，首屏只请求主详情和当前激活页签集合；其余页签在首次切换时再加载一次，页签内分页**首选**前端本地切页；数据集有界（通常不超过数百行）时一次性加载并本地切页；数据集可能很大时允许后端分页，但应在 PR 中说明理由。
- 子页签集合一旦加载完成，普通来回切换只复用本地数据；筛选变化只影响当前页签内的本地过滤和分页，不额外刷新未激活页签。
- 构建后主入口 JS gzip 目标不超过 `100KB`；超过时优先拆包并说明原因。

## 5. 测试与验证

- 任务修复或者新增行为必须 TDD：先补失败测试，再实现，再验证。
- 涉及 API client、Mock、权限、公共组件、路由、状态管理、校验或序列化时，必须补单测。
- 全局覆盖率门槛为 Statements、Branches、Functions、Lines 均不低于 90%；核心分层目录目标不低于 95%。（门禁数值以 vitest coverage 配置为准，本文档仅作参考）
- 日常开发默认使用轻量测试命令：`cd frontend && npm test`。`npm test` — 全量用例，不附带覆盖率门禁；`npm run test:coverage` — 全量用例 + 90%/95% 门禁；`npx vitest run <file> --coverage.enabled=false` — 聚焦测试，无门禁。
- 小问题修复只跑改动文件或影响模块的聚焦测试，不把覆盖率和长时间全量验证当作日常默认命令。
- 全量验证和覆盖率门禁只在显式验证时运行：`cd frontend && npm run test:coverage`。
- 聚焦测试优先使用 `npx vitest run <file> --coverage.enabled=false`；不要把 `npm test -- <file>` 当作跳过全局 coverage 门禁的方式。
- 涉及 `Dialog`、`Select`、`Popover` 等 portal 组件的测试，必须显式挂载到 `document.body` 并在 `afterEach` 清理 DOM 和 wrapper。
- 修改已导出 API 函数签名（如给 `getProjectDimensionAnalytics` 增加 filters 参数、调整参数顺序）时，必须同步全部调用点和断言该签名的测试；新增过滤参数优先放在 `(filters, projectKey)` 形态，保持与同模块其他 analytics 接口一致，避免把 `projectKey` 错位成 filters（如新接口可改用选项对象 `{ filters, projectKey }` 更不易出错）。
- 复用已有 CSS class 时要先确认没有测试用 `findAll('.xxx')` 按数量定位该 class 的元素；新增同类区块（如再加一组日期输入）应使用独立 class，避免改变既有选择器命中数量导致 `mockResolvedValueOnce`/`mockRejectedValueOnce` 队列错位、污染后续用例。
- 在 `frontend/` 目录下执行临时 Node 脚本时，默认按 ESM 语义处理，不能假设 `require()` 可用。
- 最终说明必须如实写明已执行验证、未执行项、原因、未验证范围和风险。
