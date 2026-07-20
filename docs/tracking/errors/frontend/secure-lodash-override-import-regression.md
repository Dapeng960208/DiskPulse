# lodash 安全 override 缺少 fromPairs 内部导入

## 错误内容

将 `lodash` 和 `lodash-es` override 到 `4.18.0` 后，包内 `fromPairs.js` 调用了 `baseAssignValue`，但 CommonJS 和 ESM 入口均缺少对应导入。安全审计虽可通过，运行测试或构建时仍会出现 `baseAssignValue is not defined`。

## 解决方案

通过 pnpm `patchedDependencies` 为两个包补齐 `_baseAssignValue` 导入，并将 patch 文件纳入版本控制。依赖安全 override 必须同时验证实际模块加载、全量测试和构建，不能只运行 audit。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次出现：2026-07-20 近三日代码审查修复会话
- 出现记录：`sessions/2026-07-20-recent-code-review-remediation/errors.md`
