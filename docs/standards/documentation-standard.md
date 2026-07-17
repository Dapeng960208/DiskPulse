# 文档规范（AI 快速版）

本规范用于 AI 判断什么时候改文档、文档放哪里、写到什么粒度。

## 1. 核心规则

- 文档必须基于当前代码、配置、接口和页面事实；不得把计划写成已实现。
- 未完成内容必须标注“待实现”“待验证”或“仅设计”。
- 文档内容使用简体中文；文件名、目录名使用英文 `kebab-case`。
- 配置名、接口名、权限名、表名、字段名保留英文并加反引号。

## 2. 何时必须更新文档

以下变化必须同步 `docs/`：

- 功能行为、页面路由、API 契约、配置项、权限模型。
- 数据库结构或 Alembic migration。
- 部署流程、测试入口、验证方式。
- 用户可见变化：追加到 `docs/overview/latest-features.md`。
- 开发过程、风险、阻塞、验证状态：写入 `docs/tracking/current-release.md`。

## 3. 放置边界

```text
docs/
  README.md                 # 唯一索引入口
  overview/                 # 项目级稳定说明
  guides/                   # 部署、迁移、排障、验收
  features/<feature>/       # 单功能专题
  standards/                # 规范
  tracking/                 # 当前交付、风险、错误记录
```

- 不在 `docs/` 根目录新增专题文件。
- 新文档命名和目录遵守 `docs/standards/document-naming-convention.md`。
- 可复现错误写入 `docs/tracking/error-log.md`，格式见 `docs/standards/development-error-summary.md`。

## 4. 最小内容

- 功能文档：目标、范围、入口、权限、配置、数据模型、边界、测试/验证。
- 运维指南：适用范围、前置条件、命令、验证、回滚。
- 跟踪记录：主题、已完成、风险阻塞、同步文档、验证状态。

## 5. 完成前检查

- 路由、接口、权限、配置、表名是否与代码一致。
- 网站主名称、页面标题、副标题和能力清单是否与当前实现一致，没有混入历史方案或下线功能。
- 是否写清启用条件、降级行为、未验证范围。
- 是否同步 `docs/overview/latest-features.md` 和 `docs/tracking/current-release.md`。
