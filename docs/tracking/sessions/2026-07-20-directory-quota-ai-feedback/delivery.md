# 用户目录额度调整与 AI 反馈交付记录

## 范围

- 用户目录详情为拥有 `adjust_quota` 能力的用户提供“调整额度”入口，并让详情页的内容区横向铺满。
- 前后端未传软限额时默认使用硬限额的 90%；Isilon 默认软限额宽限期为 7 天。
- AI 配额确认执行后显示实际成功、失败或取消结果。

## 交付

- `415a773 fix(quota): add directory adjustment defaults`：配额默认值、用户目录详情入口与回归测试。
- AI 确认反馈与其前端/文档回归测试单独提交，和配额默认值变更保持分离。

## 验证与风险

- 后端：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test/test_quota_adjustment.py -q`（26 passed）。
- 前端：配额调整、用户目录详情和 AI 页面定向 Vitest（29 passed）。
- 构建：`pnpm run build:test` 通过；仅有现有大体积 ECharts 产物警告。
- 浏览器：Mock 中以演示超级管理员打开 `/usage/101`，可见并打开“调整额度”；NetApp 目录默认显示 90% 软限额。
- 真实存储设备写入和 Provider 触发的 AI 确认卡仍需在隔离集成环境验证。
