# 当前 Vitest 断言扩展不支持单次组合调用

## 错误内容

`frontend/test/unit/project-storage-distribution.test.js` 使用 `toHaveBeenCalledExactlyOnceWith`，当前项目的 Vitest/Chai 断言扩展未注册该 matcher，导致测试在断言阶段报 `Invalid Chai property`。

## 解决方案

将断言拆为 Vitest 已启用的 `toHaveBeenCalledTimes(1)` 与 `toHaveBeenLastCalledWith(...)`，保留同等的调用次数和参数覆盖。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次与最近出现：2026-07-20 项目详情可用性修复会话
- 出现记录：`sessions/2026-07-20-project-detail-usability/errors.md`
