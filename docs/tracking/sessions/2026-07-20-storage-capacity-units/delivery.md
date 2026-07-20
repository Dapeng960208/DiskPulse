# 存储容量单位交付记录

## 范围

为存储容量响应补充明确的 `MB`、`GB`、`TB`、`PB` 显示单位，并让前端按服务端返回的单位展示容量值。

## 进度

- 已完成：后端以统一 `capacity.{field}={ value, unit }` 契约返回容量显示单位；前端优先展示接口返回的单位。
- 已完成：容量池、存储空间、Qtree、项目、项目组和存储集群的实时容量曲线使用 `data_unit=TB`；用户目录容量曲线使用 GB，文件数曲线使用 count。
- 已完成：存储空间监控、集群健康容量变化、容量预测、容量树、Dashboard 和 Mock 数据均补充了明确单位。
- 已完成：将容量单位、字段级 `capacity`、曲线 `data_unit` 和前端消费规则收敛为[容量单位 API 契约](../../../standards/backend/capacity-unit-contract.md)，相关功能专题改为引用该唯一来源。

## 验证

- 红灯：后端测试因尚未实现 `schemas.capacitySchema` 失败；前端测试因尚未实现 `@/utils/capacity` 失败，并确认仪表盘尚未使用接口返回的单位。
- 绿灯：`pytest` 跨接口容量契约回归 147 项通过；前端容量相关 65 项和受影响页面 32 项通过。
- 静态验证：`python -m compileall -q backend`、`pnpm run lint`、`pnpm run build:prod` 均通过；生产构建仅保留 ECharts 现有大包体积提示。

## 未验证范围

- 未连接真实 NetApp、PowerScale、QuestDB 或生产登录态；设备采集与部署环境返回需在集成环境复核。
- 待执行：绿灯及受影响的后端/前端测试。

## 未验证范围与风险

真实 NetApp、PowerScale 与生产历史数据尚未验证；本次不修改采集或数据库存储单位。
