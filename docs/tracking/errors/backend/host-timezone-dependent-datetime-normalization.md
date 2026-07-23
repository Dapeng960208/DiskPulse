# 时间转换隐式依赖或误解释应用时区

## 错误内容

存储健康分析使用无参数 `astimezone()` 和 `datetime.fromtimestamp()` 把厂商时间转换为 naive 时间，并把 naive 时间转为 NetApp `since`。Windows 开发机处于 `Asia/Shanghai` 时测试通过，GitHub Ubuntu runner 处于 UTC 时同一输入相差 8 小时，导致时间规范化、严重级别窗口和 UTC `Z` 参数共 4 项测试失败。

同类问题也出现在 DiskPulse 容量告警事件摄取：`storage_alerts.updated_at` 是上海本地 naive 墙上时间，摄取路径却直接附加 UTC 时区，使事件中心最近证据晚 8 小时。

## 解决方案

以共享时间工具显式定义 DiskPulse 应用时区 `Asia/Shanghai`：带时区时间先换算到该时区再移除时区信息，Unix 时间戳先按 UTC 瞬时解释，naive 时间按应用时区解释后再输出 UTC。任何 `replace(tzinfo=timezone.utc)` 都只能用于契约明确为 UTC 的 naive 值；本地墙上时间必须先附加应用时区再转换。回归测试必须使用显式 UTC 和供应商偏移输入，不能以执行测试的宿主机时区计算预期值。

## 备注

- 分类：`backend`
- 出现次数：2
- 首次出现：2026-07-21，GitHub Actions run `29758760754`
- 最近出现：2026-07-23，`2026-07-23-questdb-utc-time-contract`
- 出现记录：
  - `sessions/2026-07-21-github-actions-timezone-and-lockfile/errors.md`
  - `sessions/2026-07-23-questdb-utc-time-contract/errors.md`
