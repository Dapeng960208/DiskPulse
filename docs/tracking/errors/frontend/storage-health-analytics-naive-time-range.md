# 存储集群健康分析前端传递无时区时间范围

## 错误内容

存储集群详情的容量、性能、故障分析页签和健康报告导出直接发送时间选择器返回的 `YYYY-MM-DD HH:mm:ss` 本地墙上时间。请求 URL 将空格编码为 `+`，FastAPI 将其解析为无时区 `datetime`；健康分析接口要求 `start_time` 与 `end_time` 都带时区，因此返回 `422 Unprocessable Content`。

## 解决方案

在所有健康分析请求与导出入口使用 `toUtcRange`，把用户展示时区的本地时间转换为 RFC 3339 UTC `Z` 边界。后端继续拒绝无时区参数，避免隐式猜测用户或服务器时区。

## 备注

- 分类：`frontend`
- 首次与最近出现：2026-07-24。
- 出现次数：1。
- 出现记录：`sessions/2026-07-24-storage-health-analytics-utc-range/errors.md`。
