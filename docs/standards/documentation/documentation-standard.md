# 文档规范

## 事实与范围

- 文档必须与当前代码、配置、接口和页面一致；计划、假设和未验证结论必须明确标记。
- 文档内容使用简体中文；代码标识、配置名、路径和接口使用反引号保留原文。
- 同一行为只保留一个事实来源。其他专题通过相对 Markdown 链接引用，不复制接口、权限、配置或验证结论。

## 分类与放置

文档先按一级领域确定职责，再按二级主题确定归属；不得把同一功能分散到平铺目录。

| 一级领域 | 二级主题 | 放置规则 |
| --- | --- | --- |
| `overview/` | `product/`、`architecture/` | 稳定的产品、系统、前端、后端和数据库说明。 |
| `standards/` | `frontend/`、`backend/`、`database/`、`documentation/`、`git/` | 强制规范按专业域放置。 |
| `features/` | `<领域>/<功能>/` | 功能事实来源；同一功能的概览、后端、前端、设计和操作说明必须同目录。 |
| `guides/` | `<专业域>/` | 可执行的测试、排障、部署和验收步骤。 |
| `tracking/` | 固定文件 | 仅记录当前交付状态和可复现错误。 |

当前功能领域为 `ai`、`storage`、`identity`、`organization`、`experience`。AI 相关功能一律放在 `docs/features/ai/<功能>/`；不得创建 `docs/features/ai-*` 平铺目录。新增一级领域前先更新 [文档索引](../../README.md)，说明其边界和二级功能。

跨分类关联只能链接到目标专题的事实来源。例如 AI 配额工具引用存储配额专题，不在 AI 目录复制配额 API 或设备写回规则。

## 必须更新的情形

功能行为、路由、API、配置、权限、数据库、部署方式、测试入口或用户可见结果改变时，更新对应功能专题。用户可见能力同步更新[当前能力](../../overview/product/current-capabilities.md)，当前交付和风险同步更新[当前交付](../../tracking/current-release.md)。

可复现且有复用价值的失败按[错误记录规则](./development-error-summary.md)写入 `docs/tracking/error-log.md`。

## 命名、移动与完成检查

命名、移动和链接规则见[文档命名与链接](./document-naming-convention.md)。开发开始前的必读文档由[开发阅读矩阵](./development-reading-guide.md)确定。

交付前确认路由、接口、权限、配置、数据模型和页面文案与实现一致，并明确未验证范围和部署前提。
