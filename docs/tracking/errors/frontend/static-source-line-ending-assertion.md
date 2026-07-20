# 静态源码换行断言与 Windows CRLF 不兼容

## 错误内容

`frontend/test/unit/project-context-tabs.test.js` 将 Vue 源码片段的换行固定为 LF，Windows 工作区读取到 CRLF 后，语义正确的页签断言仍失败。

## 解决方案

静态源码断言使用 `\r?\n` 匹配平台换行；行为验证继续由挂载测试和 API 参数断言覆盖，不以换行格式判断功能正确性。

## 备注

- 分类：`frontend`
- 出现次数：2
- 首次与最近出现：2026-07-20 项目详情可用性修复会话、主分支合并验证
- 出现记录：`sessions/2026-07-20-project-detail-usability/errors.md`、`sessions/2026-07-20-project-detail-usability-merge/errors.md`
