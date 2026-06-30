# 文档命名与放置规范（AI 快速版）

本规范用于 AI 新增或移动内部维护型 Markdown 文档时快速判断位置和命名。

## 1. 命名规则

- 文件名和目录名使用英文 `kebab-case`。
- 文档内容使用简体中文。
- 禁止中文文件名、中文目录名。
- 禁止无语义名称：`new.md`、`temp.md`、`final-v2.md`。

## 2. 固定目录

```text
docs/
  README.md                 # 唯一索引入口
  overview/                 # 项目概览、架构、最新功能
  guides/                   # 部署、迁移、排障、验收
  features/<feature>/       # 单功能专题
  standards/                # 开发和文档规范
  tracking/                 # 当前交付、风险、错误记录
```

- 不在 `docs/` 根目录新增专题文件。
- 新专题优先放 `docs/features/<feature>/`。

## 3. 常用文件名

- 功能专题：`requirements.md`、`backend.md`、`frontend.md`、`test-plan.md`、`verification.md`。
- 指南：`deployment-guide.md`、`database-migrations.md`、`troubleshooting-console-logs.md`、`verification-checklist.md`。

## 4. 链接维护

- 文档内部链接优先使用相对路径。
- 移动或重命名文件时，全仓搜索旧路径并同步更新引用。
