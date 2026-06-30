# 前端测试与覆盖率说明

## 目标

- 当前前端测试体系基于 `Vitest + @vue/test-utils + jsdom`。
- 覆盖率统计范围为 `frontend/src/**/*.{js,vue}`。
- 初版覆盖率门禁为全局 `lines`、`statements`、`branches` 均不低于 `70%`。
- `functions` 继续纳入覆盖率报告，但本轮不作为硬门禁；后续如需提升到全指标 `70%+`，需要继续补足页面交互与事件处理测试。

## 测试入口

在 `frontend/` 目录执行：

```powershell
npm test
npm run test:coverage
```

- `npm test`：运行全部前端测试，不校验覆盖率阈值。
- `npm run test:coverage`：运行全部前端测试，并校验 `frontend/src` 的全局覆盖率门禁。

## 聚焦运行

需要只验证单个文件或单组测试时，优先使用 `vitest` 自带过滤能力，避免每次都跑全量覆盖率。

```powershell
npx vitest run test/unit/router/index.test.js --coverage.enabled=false
npx vitest run test/unit/smoke/surface-regression.test.js --coverage.enabled=false
```

## 目录约定

```text
frontend/
  test/
    helpers/      # mount 包装、公共测试辅助
    setup.js      # 全局 mock、DOM 清理、浏览器 API stub
    unit/         # 单元测试与轻量 smoke test
```

## Mock 约定

- 优先在 `test/setup.js` 处理通用浏览器 API stub，例如 `window.open`、`URL.createObjectURL`。
- 组件级依赖使用测试文件内的 `vi.mock()` 就近声明，避免把页面特有 mock 扩散成全局默认行为。
- 对 `element-plus`、`vue-router`、`js-cookie`、请求封装等常见依赖，优先使用轻量 stub，保证测试关注业务分支而不是第三方组件实现。
- 活跃页面覆盖以 shallow/smoke 为主，图表、复杂表格和上传能力默认 stub 掉重量级子组件。

## 当前覆盖策略

- 优先覆盖 `utils`、`api/support`、`composables`、`stores`、`router` 的关键逻辑分支。
- 对当前路由实际使用的页面补充基础 smoke test，保护模板渲染、布局挂载和主要事件入口。
- 不通过缩小 `include` 范围或排除业务代码来抬高覆盖率数字；仅排除静态资源、样式和纯入口文件。

## 已验证结果

截至 `2026-06-30`，执行 `npm run test:coverage` 后，`frontend/src` 的全局覆盖率结果为：

- `statements`: `89.70%`
- `branches`: `81.06%`
- `lines`: `89.70%`
- `functions`: `47.30%`

本轮门禁已满足初版 `70%+` 覆盖率目标；`functions` 指标仍需在后续通过更细的交互测试继续提升。
