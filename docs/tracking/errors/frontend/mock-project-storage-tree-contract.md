# Mock 项目存储树响应未覆盖分布图契约

## 错误内容

项目详情的存储分布改为读取 `GET /projects/{project_id}/storage-tree?value_type=used` 后，Mock 仍返回扁平项目组对象，缺少树形 `children`、用于面积计算的 `value` 和用户节点，导致本地演示不能呈现“项目组 → 用户”分布。

## 解决方案

Mock 按接口语义从当前项目组和用户目录记录构造项目组 → 用户树，并同时返回 `used` 与 `value`；聚焦用例覆盖响应层级和数值字段。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次与最近出现：2026-07-20 项目详情可用性修复会话
- 出现记录：`sessions/2026-07-20-project-detail-usability/errors.md`
