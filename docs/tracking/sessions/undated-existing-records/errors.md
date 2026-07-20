# 原平铺错误记录迁移

原 `docs/tracking/error-log.md` 没有记录来源会话或具体日期。本文件仅保留迁移关系；每类错误按已列出的一次历史出现计数，后续实际出现时再在对应事实文档中追加并计数。

| 错误标题 | 分类事实文档 | 本次计数 |
| --- | --- | ---: |
| 前端 Vitest 从仓库根目录运行 | [错误详情](../../errors/frontend/vitest-working-directory.md) | 1 |
| 系统 Python 或 pytest 命令不可用 | [错误详情](../../errors/environment/python-test-command.md) | 1 |
| 将本地自动化等同于外部集成验收 | [错误详情](../../errors/integration/external-verification.md) | 1 |
| 使用前端 Mock 代替授权验证 | [错误详情](../../errors/frontend/mock-not-authorization.md) | 1 |
