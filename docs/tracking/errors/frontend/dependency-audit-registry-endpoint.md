# 镜像仓库缺少 pnpm 安全审计端点

## 错误内容

在使用 `registry.npmmirror.com` 的环境执行 `pnpm audit` 时返回 `ERR_PNPM_AUDIT_ENDPOINT_NOT_EXISTS`，因为该镜像没有实现 `/-/npm/v1/security/audits/quick`。这会让依赖安装正常但安全门禁无法运行。

## 解决方案

项目脚本 `pnpm run audit:high` 显式指定 `https://registry.npmjs.org`，只把官方审计结果作为依赖漏洞门禁；安装源仍可按本地环境配置。提交前要求高危和严重漏洞为零。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次出现：2026-07-20 近三日代码审查修复会话
- 出现记录：`sessions/2026-07-20-recent-code-review-remediation/errors.md`
