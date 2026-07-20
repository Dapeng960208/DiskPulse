# 前端构建脚本名不一致

## 错误内容

在 `frontend/` 执行通用命令 `pnpm run build` 返回 `ERR_PNPM_NO_SCRIPT Missing script: build`。仓库只定义了 `build:test` 和 `build:prod`。

## 解决方案

先检查 `frontend/package.json` 或 `frontend/README.md`，生产构建使用 `pnpm run build:prod`，测试模式构建使用 `pnpm run build:test`。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次与最近出现：2026-07-20 项目使用量与成员默认权限会话
- 出现记录：`sessions/2026-07-20-project-usage-reader-default/errors.md`
