# 前后端覆盖率、Warning 收敛与 GitHub Actions 设计

## 状态

已实现；本地验证完成，GitHub-hosted runner 尚待远端执行确认。

## 目标

- 使用当前基线 Node `22.14.0`、Python `3.13.0`，建立唯一 GitHub Actions workflow。
- 让后端和前端全量测试、覆盖率、lint、build 都能在 CI 中执行，并以覆盖率作为门禁。
- 修复项目代码、配置或测试挂载造成的重复 warning；不使用全局 blanket silence 掩盖问题。
- 复用现有测试入口和依赖，只补最少的测试、阈值或必要配置。

## 当前基线

- 后端：全量 pytest 为 `338 passed`，覆盖率 `88%`，`38 warnings`。
- 前端：覆盖率命令包含 `43` 个文件、`240` 个用例，存在 `3` 个既有契约失败；重复输出 Sass `legacy-js-api`、Vue `loading directive` 等 warning。
- 后端当前入口为 `python -m coverage run -m pytest`、`python -m coverage report`；`.coveragerc` 当前 `fail_under = 85`。
- 前端当前入口为 `npm run test:coverage`、`npm run lint`、`npm run build:prod`；Vitest 当前覆盖率阈值仍低于最终目标。
- 以上结果是实现前基线。前端契约失败和后端 warning 未解决前，CI 不能标记为绿色。

## 范围与文件边界

### 后续允许修改的实现文件

- `.github/workflows/coverage-ci.yml`：唯一 workflow，负责固定运行时、依赖安装、测试覆盖率、lint 和 build。
- `.coveragerc`、`backend/test/` 及产生 warning 的最小后端源文件：提高覆盖率门禁、补缺失分支测试、修复 warning 根因。
- `frontend/vitest.config.js`、`frontend/test/` 及产生 warning 的最小前端源文件：提高覆盖率门禁、修复既有契约、补缺失测试。
- `frontend/vite.config.js`、`frontend/package.json` 和对应 lockfile：仅在 Sass 现代 API 与现有依赖版本确实不兼容时调整。

### 本设计不包含

- 不新增第二个 GitHub Actions workflow。
- 不切换 npm/pnpm，不新增测试框架或覆盖率服务。
- 不通过缩小 coverage `include`、扩大 `omit`、删除失败用例或统一静默 warning 提高数字。
- 本轮文档任务不修改上述实现文件，也不修改其他 `docs/` 文件。

## 方案

### 1. 唯一 CI 流程

`coverage-ci.yml` 在 `push` 和 `pull_request` 触发，使用一个 job，步骤顺序固定为：

1. checkout。
2. 使用 `actions/setup-node` 固定 Node `22.14.0`，以 `frontend/package-lock.json` 做 npm 缓存依据。
3. 使用 `actions/setup-python` 固定 Python `3.13.0`，安装 `backend/requirements.txt` 中的现有依赖。
4. 在 `backend/` 入口之外从仓库根目录执行后端全量 coverage：

   ```powershell
   python -m coverage erase
   python -m coverage run -m pytest backend/test -q
   python -m coverage report --fail-under=85
   ```

5. 在 `frontend/` 执行：

   ```powershell
   npm ci
   npm run test:coverage
   npm run lint
   npm run build:prod
   ```

6. 任一步骤非零退出即失败；不自动切换 Python、Node 或包管理器，不以重试掩盖确定性失败。

### 2. 覆盖率门禁

- 后端沿用 `.coveragerc` 的 source/omit 范围，`fail_under` 设为 `85`。
- 前端沿用 Vitest 当前 `src/**/*.{js,vue}` 统计范围和已有排除项，`statements`、`branches`、`functions`、`lines` 均设为 `80`。
- 当前后端 `88%`、前端既有契约失败及尚未确认的前端四项指标不能被虚报为达标。若补测后仍低于对应门槛，保留 CI 失败并在实现交付中明确列出剩余缺口。
- 补测只针对未覆盖的真实业务分支、错误路径和页面契约；不为覆盖率引入无业务价值的测试或排除规则。

### 3. Warning 根因修复

- 先运行完整测试并按 warning 类别、来源文件和调用路径分类，区分项目 warning 与第三方依赖 warning。
- 后端对项目拥有的 warning 在产生点修复，并用最小回归测试确认；只对无法控制且有明确模块/类别边界的第三方 warning 使用局部、可解释的过滤，不添加全局 `ignore`。
- Sass `legacy-js-api`：移除或缩小现有 `silenceDeprecations`，优先使用当前 Vite/Sass 组合支持的现代 API；如果基线依赖不支持，才升级现有依赖并同步 lockfile，随后验证构建结果和样式输出。
- Vue `loading directive`：复用 `frontend/test/helpers/mount.js` 的测试辅助，在需要 `v-loading` 的挂载路径提供明确的 `loading` directive stub；不在 Vitest 或 Vue 全局关闭 warning。
- 不使用 `--disable-warnings`、全局 `warnings.filterwarnings("ignore")` 或等价的 blanket silence。warning 必须被消除、局部解释或作为明确的未验证风险保留。

### 4. 既有前端契约失败

- 先单独复现并确认 `3` 个失败用例对应的真实页面/接口契约。
- 以当前实现和已确认设计为准修复断言或实现，不删除用例、不扩大 mock 范围规避失败。
- 复现用例恢复通过后，再执行同一入口的 `npm run test:coverage`，确保修复没有绕开全量覆盖率统计。

## 数据与命令流程

```text
固定 Node/Python
        |
        +--> 安装 frontend/package-lock.json 与 backend/requirements.txt 依赖
        |
        +--> 后端全量 pytest --> coverage report --> 85% 门禁
        |
        +--> 前端全量 Vitest --> coverage thresholds --> 80% 门禁
        |
        +--> frontend lint --> frontend production build
        |
        +--> 任一步骤失败，workflow 失败并保留命令输出
```

覆盖率统计只来自现有源码范围；测试结果、覆盖率和 warning 输出以 CI 日志为准，不上传或依赖外部覆盖率服务。

## 失败处理

- 依赖安装失败：直接失败，检查固定版本、lockfile 和 runner 环境；不得偷偷改用另一包管理器。
- 后端或前端测试失败：保留失败输出，优先修复根因；不能通过跳过测试、删测试或静默 warning 放行。
- 后端覆盖率低于 `85%` 或前端覆盖率低于 `80%`：CI 失败，补真实测试或明确记录待实现项；不扩大排除范围。
- lint/build 失败：CI 失败，按对应源文件修复；构建已有的非重复、非阻断提示必须与本主题 warning 分开记录。
- 第三方 warning 无法在当前依赖版本消除：必须限定到具体模块和 warning 类别，并在实现验证中说明升级条件和残余风险。

## 验证标准

实现完成后至少满足：

- 仓库只存在一个本主题 GitHub Actions workflow，日志明确显示 Node `22.14.0` 和 Python `3.13.0`。
- 后端全量 pytest 通过，覆盖率报告可生成并达到四项指标最终 `85%` 门禁；warning 数量相对基线下降，项目拥有的重复 warning 清零。
- 前端全量测试通过，`3` 个既有契约失败已修复，coverage 命令可生成报告并达到四项指标最终 `80%` 门禁。
- `npm run lint` 和 `npm run build:prod` 通过。
- Sass、Vue loading warning 已在产生点或测试挂载边界修复；代码中没有新增全局 blanket silence。
- 本地复现命令与 CI 命令一致，且执行结果、未验证范围和残余 warning 均如实记录。

## 未验证风险

- 本设计编写阶段未重新运行后端/前端全量测试，当前基线数字来自已确认结果，不是本次文档变更后的新验证。
- 后端 `38 warnings` 的具体类别和归属尚未在本轮重新采样；实现时可能需要逐条定位第三方兼容性。
- 前端四项 coverage 当前实际数值、3 个契约失败的具体断言及现代 Sass API 与现有 Vite 版本的兼容性尚未验证。
- GitHub-hosted runner 的网络、依赖安装速度和真实构建环境未验证；CI 失败时应区分代码失败与环境失败。
