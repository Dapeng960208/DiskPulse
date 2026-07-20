# AI 历史超级管理员可见性修复

## 范围

修复会话所属超级管理员无法读取缺少可见性范围标记的旧 AI 历史回复；普通用户继续保持关闭式隐藏。

## 已完成

- 为超级管理员本人会话的旧未知范围历史补充回归测试。
- 调整历史可见性判定，不改变会话 `user_id` 隔离或普通用户的范围校验。
- 更新 AI 对话事实文档、当前能力和错误记录。

## 验证

- `D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m pytest test\\test_ai_history_security.py -q --basetemp <writable-temp>`：13 passed。
- `D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m coverage run --source=services.ai_chat_service -m pytest test\\test_ai_history_security.py test\\test_ai_services.py -q --basetemp <writable-temp>`：34 passed；`coverage report --fail-under=80 services\\ai_chat_service.py`：84%。

## 未验证范围与风险

- 未在真实浏览器及生产 Provider 上验证；本次不涉及 Provider 调用、数据库迁移或跨用户会话访问。
