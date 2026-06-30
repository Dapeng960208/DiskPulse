# 错误记录

### 2026-06-30：覆盖率门禁缺少本地工具
- 触发：执行 `.\.venv\Scripts\python.exe -m coverage --version` 和后续覆盖率门禁。
- 现象：本地虚拟环境提示 `No module named coverage`。
- 根因：后端依赖文件未声明 `coverage`，本地 `.venv` 也未安装该包。
- 修复：在 `backend/requirements.txt` 补充 `coverage==7.13.0`，并执行 `.\.venv\Scripts\python.exe -m pip install coverage==7.13.0`。
- 验证：`.\.venv\Scripts\python.exe -m coverage run -m unittest discover -s backend\test -p "test_*.py"; .\.venv\Scripts\python.exe -m coverage report` 通过，核心后端覆盖率 `73%`。
- 风险：新环境需要重新安装依赖后才能执行覆盖率门禁。

### 2026-06-30：导出接口响应类型与文件类型不一致
- 触发：新增核心 API 测试覆盖 `storage-usages/export/` 和 `large-files/export/`。
- 现象：存储使用 PDF 导出返回 Excel MIME，Excel 导出返回 `application/pdf`；大文件 `.xlsx` 导出也返回 `application/pdf`。
- 根因：路由中 `media_type` 常量写反或沿用了错误值。
- 修复：修正 `backend/routers/storage_usage.py` 和 `backend/routers/large_files.py` 的导出 `media_type`。
- 验证：`.\.venv\Scripts\python.exe -m unittest backend.test.test_core_api` 通过。
- 风险：只验证了响应头和路由契约，未打开真实导出文件做人工内容验收。

### 2026-06-30：手动存储设备测试脚本包含真实连接信息
- 触发：审查后端测试和手动集成脚本。
- 现象：`backend/test/test_netapp.py`、`backend/test/test_isilon.py` 中存在真实设备地址、用户名和密码。
- 根因：手动验证脚本与自动测试目录混放，连接配置直接写在源码中。
- 修复：改为读取 `NETAPP_*`、`ISILON_*` 环境变量；NetApp 手动函数去掉 `test_` 前缀，避免自动测试误识别。
- 验证：`.\.venv\Scripts\python.exe -m unittest discover -s backend\test -p "test_*.py"` 通过，未触发真实外部连接。
- 风险：真实设备连通性未验证，需由具备环境变量的人工环境单独执行脚本。

### 2026-06-30：规范引用文件与当前仓库结构不一致
- 触发：按 `AGENTS.md` 和项目标准读取必读文档、前端样式入口。
- 现象：`docs/standards/domain-terminology.md` 不存在；`frontend/src/style.css` 不存在。
- 根因：规范引用仍指向旧文件，当前仓库实际样式入口为 `frontend/src/styles/style.scss`。
- 修复：本次认证交付先按现有实际文件执行，并在认证文档与交付记录中避免引用不存在入口。
- 验证：已确认 `docs/standards/` 下无 `domain-terminology.md`，前端实际入口由 `frontend/src/main.js` 引入 `frontend/src/styles/style.scss`。
- 风险：后续任务仍可能按旧规范路径寻找文件，需要补齐或修订标准文档。
