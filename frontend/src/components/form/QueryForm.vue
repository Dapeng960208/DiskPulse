<script setup>
import { ElButton, ElForm } from 'element-plus';
import { computed, ref, useSlots } from 'vue';
import GridContainer from '../basic/GridContainer.vue';

const emit = defineEmits(['reset', 'query', 'export']);
const showAdvancedFilters = ref(false);
const slots = useSlots();
const hasAdvancedSlot = computed(() => slots.advanced != null);
const hasExportExcelSlot = computed(() => slots.exportExcel != null);
</script>

<template>
  <div class="query-form-bar">
    <ElForm
      class="w-full h-full"
      label-width="auto"
      inline>
      <GridContainer
        cols="auto"
        min-col-width="280px">
        <slot></slot>
        <TransitionGroup name="list">
          <slot
            v-if="showAdvancedFilters"
            name="advanced"></slot>
        </TransitionGroup>
        <template #tail>
          <slot name="actions"></slot>
          <ElButton
            v-if="hasAdvancedSlot"
            type="primary"
            text
            @click="showAdvancedFilters = !showAdvancedFilters"
          >
            更多
            <i
              v-if="showAdvancedFilters"
              class="i-ri-arrow-up-s-line"></i>
            <i
              v-else
              class="i-ri-arrow-down-s-line"></i>
          </ElButton>

          <ElButton
            type="primary"
            @click="emit('query')"
          >
            <i class="i-ri-search-line"></i>
            搜索
          </ElButton>
          <ElButton @click="emit('reset')">
            <i class="i-ri-reset-right-line"></i>
            重置
          </ElButton>
          <ElButton
            v-if="hasExportExcelSlot"
            type="success"
            @click="emit('export')"
          >
            导出
          </ElButton>
        </template>
      </GridContainer>
    </ElForm>
  </div>
</template>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';

// 搜索栏容器
.query-form-bar {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-md) var(--spacing-xl);
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;

  // 左侧搜索图标装饰线
  border-left: 3px solid var(--primary-color);

  @include mobile {
    padding: var(--spacing-md);
  }
}

// 表单样式
:deep(.el-form) {
  .el-form-item {
    margin-bottom: 0;
    align-items: center;

    .el-form-item__label {
      font-size: var(--font-size-sm);
      color: var(--text-primary);
      font-weight: var(--font-weight-medium);
      line-height: var(--line-height-normal);
      display: flex;
      align-items: center;
      white-space: nowrap;
    }

    .el-form-item__content {
      .el-input,
      .el-select,
      .el-date-editor {
        .el-input__wrapper {
          border-radius: var(--radius-md);
          box-shadow: none;
          transition: var(--transition-base);
          border: 1px solid var(--border-color);
          background: var(--bg-secondary);

          @include input-focus;

          &:hover {
            border-color: var(--border-dark);
            background: var(--bg-primary);
          }

          .el-input__inner {
            font-size: var(--font-size-sm);
            color: var(--text-primary);

            &::placeholder {
              color: var(--text-disabled);
            }
          }
        }
      }

      .el-select {
        .el-select__wrapper {
          border-radius: var(--radius-md);
          box-shadow: none;
          transition: var(--transition-base);
          border: 1px solid var(--border-color);
          background: var(--bg-secondary);

          @include input-focus;

          &:hover {
            border-color: var(--border-dark);
            background: var(--bg-primary);
          }
        }
      }
    }
  }
}

// 按钮样式
:deep(.el-button) {
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-base);
  padding: 8px 16px;
  height: 32px;

  &.el-button--primary {
    @include button-primary;

    &.is-text {
      background: transparent;
      color: var(--primary-color);
      border: none;
      height: auto;
      padding: 4px 8px;

      &:hover {
        background: var(--bg-hover);
        color: var(--primary-dark);
        transform: none;
        box-shadow: none;
      }
    }
  }

  &.el-button--default {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    color: var(--text-secondary);

    &:hover {
      background: var(--bg-hover);
      border-color: var(--primary-color);
      color: var(--primary-color);
    }
  }

  &.el-button--success {
    background: var(--success-color);
    border-color: var(--success-color);
    color: white;

    &:hover {
      background: var(--success-light);
      border-color: var(--success-light);
      transform: translateY(-1px);
      box-shadow: var(--shadow-md);
    }
  }

  i {
    margin-right: var(--spacing-xs);
    font-size: 14px;
  }
}

// 动画效果
.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease-in-out;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

// 网格容器样式
:deep(.grid-container) {
  gap: var(--spacing-md) var(--spacing-lg);
  align-items: center;

  .grid-tail {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
    justify-content: flex-end;
  }
}

// 响应式设计
@include mobile {
  :deep(.grid-container) {
    .grid-tail {
      justify-content: center;

      .el-button {
        flex: 1;
        min-width: 80px;
      }
    }
  }
}
</style>
