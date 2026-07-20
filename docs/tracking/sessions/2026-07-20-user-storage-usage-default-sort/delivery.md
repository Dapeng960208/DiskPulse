# 用户列表存储用量默认排序交付

## 范围

用户信息管理页面的用户表首次加载和重置筛选时，默认按存储用量从高到低展示。

## 已完成

- 页面初始查询参数固定为 `prop=storage_used`、`order=descending`。
- 搜索筛选与重置沿用同一查询状态；用户手动点击表头后，仍按选定字段与方向请求。
- 新增前端回归测试，验证首次请求明确携带该排序参数。

## 验证

- RED：`cd frontend; pnpm exec vitest run test/unit/user-management-ldap-sync.test.js -t "requests users by storage usage descending by default" --coverage.enabled=false`，在实现前失败。
- GREEN：同一命令在实现后通过（`1 passed`）。
- ESLint：`pnpm exec eslint src/pages/admin/user/UserListPage.vue test/unit/user-management-ldap-sync.test.js`，0 error；测试桩已有 9 条 `vue/one-component-per-file` warning。

## 未验证范围和风险

- 浏览器端到端与真实后端未执行；后端的无排序参数兜底降序保持不变。
- 扩展运行整个 `user-management-ldap-sync.test.js` 时有两项既有失败，根因是测试未为当前 `TableActionButton` 配置桩，导致找不到“新增用户/同步LDAP”按钮；与本次默认排序逻辑无关，未扩展修改范围。
