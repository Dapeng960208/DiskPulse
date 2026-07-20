# 项目组编辑回传只读响应字段导致 422

## 错误内容

项目组列表返回 `capabilities` 和计算字段 `capacity`。编辑表单复制整行数据并提交时，这些字段会被提交到 `PUT /storage-pulse/api/groups/{group_id}`；写入模型禁止额外字段，接口返回 `422 Unprocessable Content`。

## 解决方案

项目组表单按可写字段构造请求体，只发送表单实际维护的项目、存储目标、通知、监控和结项字段；不以删除部分响应字段的黑名单方式构造写入请求。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次与最近出现：2026-07-20 项目组编辑校验失败会话
- 出现记录：`sessions/2026-07-20-group-update-validation/errors.md`
