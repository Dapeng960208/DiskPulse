# Tooltip 同时使用 focus 与 click 导致点击后立即关闭

## 错误内容

Element Plus `ElTooltip` 同时配置 `focus` 与 `click` 触发后，点击可聚焦元素时先由 `focus` 打开，再由同一次点击触发 `click` 切换，最终立即关闭。静态属性和单元测试均可能通过，但真实页面中看不到 Tooltip。

## 解决方案

需要同时支持鼠标和键盘时使用 `['hover', 'focus']`：鼠标悬停由 `hover` 处理，键盘 Tab 与鼠标点击造成的聚焦由 `focus` 处理。不要把 `focus` 与会切换状态的 `click` 同时配置在同一 Tooltip 上；通过真实浏览器从未聚焦状态验证一次焦点进入和浮层可见性。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次与最近出现：2026-07-22 容量基线算法说明会话
- 出现记录：`sessions/2026-07-22-capacity-baseline-algorithm-explanation/errors.md`
