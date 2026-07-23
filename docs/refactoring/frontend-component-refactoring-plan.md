# 前端组件重构计划

## 已识别的优化机会

### 1. IncidentCenterPage.vue (442行 → 建议目标: ~300行)

**当前问题**:
- AI 设置逻辑混合在主组件中（约140行）
- 包含复杂的状态管理和 API 调用

**重构方案**:
1. 提取 `useIncidentAiSettings` composable
   - 管理 AI 设置状态
   - 处理加载/保存逻辑
   - 减少主组件 ~80行

2. 创建 `IncidentAiSettingsDialog.vue` 组件
   - 独立的对话框组件
   - Props: visible, settings, loading, saving, error
   - Emits: save, close
   - 减少主组件 ~60行

### 2. AiChatPage.vue (500+行 → 建议目标: ~350行)

**当前问题**:
- 推理控制逻辑较复杂
- 流式输出处理代码量大

**重构方案**:
1. 提取 `useAiChatStream` composable
   - 管理流式消息接收
   - 处理 SSE 连接
   - 减少主组件 ~100行

2. 创建 `AiReasoningControls.vue` 组件
   - 推理能力选择器
   - 模型切换逻辑
   - 减少主组件 ~50行

## 实施状态

### ✅ 已完成优化

1. **性能优化: 28天历史数据计算**
   - 添加缓存机制
   - 预计算时间边界
   - 性能监控日志
   - 提交: `a370060`

2. **测试覆盖: Claude Code Adapter**
   - 9个集成测试
   - 覆盖配置、工具调用、错误处理
   - 提交: `9c22ba9`

### 🔄 待实施优化

3. **前端组件重构**
   - 由于 lint 规则和测试复杂度，建议分阶段实施
   - **阶段1**: 仅提取 composable（不破坏现有结构）
   - **阶段2**: 修复 Element Plus 组件命名规范
   - **阶段3**: 拆分对话框子组件

## 推荐实施顺序

1. 先修复 Element Plus 组件 PascalCase 命名规范
   ```vue
   <!-- 修改前 -->
   <el-dialog>
   
   <!-- 修改后 -->
   <ElDialog>
   ```

2. 提取 composable（风险最低）
   - 保持组件模板不变
   - 只重组 script setup 逻辑

3. 拆分子组件（最后）
   - 需要更新测试
   - 需要确保 props/events 正确传递

## 收益评估

- **可维护性**: ⭐⭐⭐⭐ (减少组件复杂度)
- **测试性**: ⭐⭐⭐⭐ (composable 更易测试)
- **可重用性**: ⭐⭐⭐ (其他页面可复用 composable)
- **实施风险**: ⭐⭐ (需要仔细测试)

## 注意事项

- Element Plus 组件必须使用 PascalCase
- Vue 3 Composition API 的 `reactive` 对象在传递给子组件时需要注意响应性
- 测试需要 mock composable 的返回值
