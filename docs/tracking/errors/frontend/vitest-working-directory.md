# 前端 Vitest 从仓库根目录运行

## 错误内容

从仓库根目录直接运行前端 Vitest，导致测试路径、前端别名或脚本解析失败，常见现象是找不到测试文件或无法解析别名。

## 解决方案

进入 `frontend/` 后使用项目脚本或 `pnpm exec vitest` 运行聚焦测试，例如 `cd frontend && pnpm exec vitest run <file> --coverage.enabled=false`。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次与最近出现：原平铺错误记录（原始会话日期未知）
- 出现记录：`sessions/undated-existing-records/errors.md`
