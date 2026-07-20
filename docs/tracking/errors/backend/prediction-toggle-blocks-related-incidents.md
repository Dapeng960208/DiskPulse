# 预测发布开关错误阻断关联事件

## 错误内容

项目成员已经通过资源 `reader` 权限校验，但在 `capacity_prediction_settings.user_visible=false` 时读取本项目关联事件仍收到 `403 capacity prediction is globally disabled`。

## 解决方案

`list_resource_related_incidents` 只保留当前资源项目 RBAC 校验；预测详情、最终预测列表、容量计划和预测能力接口继续受发布开关控制。Mock 使用相同边界，跨项目请求仍返回 403。

## 备注

- 分类：`backend`
- 出现次数：1
- 首次与最近出现：2026-07-20 导航信息架构会话
- 出现记录：`sessions/2026-07-20-navigation-information-architecture/errors.md`
