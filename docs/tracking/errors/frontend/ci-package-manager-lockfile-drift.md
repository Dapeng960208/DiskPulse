# CI 混用前端包管理器与过期锁文件

## 错误内容

前端已声明 `pnpm@10.34.4` 并以 `pnpm-lock.yaml` 维护依赖，但 Coverage CI 仍执行 `npm ci` 并读取过期的 `package-lock.json`，本地复现为 npm peer dependency `ERESOLVE`。切换到 pnpm 后，权威 lockfile 的 patched dependencies 配置也曾与 `package.json` 不一致，`pnpm install --frozen-lockfile` 报 `ERR_PNPM_LOCKFILE_CONFIG_MISMATCH`。

## 解决方案

仓库只保留 `pnpm-lock.yaml`，Coverage CI 先安装 `packageManager` 声明的 pnpm 版本，再使用 pnpm cache、`pnpm install --frozen-lockfile` 和 pnpm 脚本执行覆盖率、lint、构建。增加静态 CI 契约测试，禁止重新引入 npm 安装步骤或第二份 lockfile；依赖或 patch 变化后必须先在干净安装路径验证 frozen lockfile。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次出现：2026-07-21，`2026-07-21-github-actions-timezone-and-lockfile`
- 最近出现：2026-07-21，`2026-07-21-github-actions-timezone-and-lockfile`
- 出现记录：`sessions/2026-07-21-github-actions-timezone-and-lockfile/errors.md`
