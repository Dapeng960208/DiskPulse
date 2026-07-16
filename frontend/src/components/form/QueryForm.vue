<script setup>
import { ElButton, ElForm } from 'element-plus';
import { computed, ref, useSlots } from 'vue';

defineProps({
  advancedCount: {
    type: Number,
    default: 0,
  },
});

const emit = defineEmits(['reset', 'query', 'export']);
const showAdvancedFilters = ref(false);
const slots = useSlots();
const hasAdvancedSlot = computed(() => slots.advanced != null);
const hasActiveFiltersSlot = computed(() => slots['active-filters'] != null);
const hasExportExcelSlot = computed(() => slots.exportExcel != null);
</script>

<template>
  <div class="query-form-bar">
    <ElForm
      class="query-form"
      @submit.prevent="emit('query')">
      <div class="query-form__toolbar">
        <div class="query-form__fields">
          <slot></slot>

          <Transition name="filter-expand">
            <div
              v-if="showAdvancedFilters"
              id="query-form-advanced"
              class="query-form__advanced">
              <slot name="advanced"></slot>
            </div>
          </Transition>
        </div>

        <div class="query-form__actions">
          <slot name="actions"></slot>
          <ElButton
            v-if="hasAdvancedSlot"
            class="query-form__more"
            text
            native-type="button"
            :aria-expanded="showAdvancedFilters"
            aria-controls="query-form-advanced"
            @click="showAdvancedFilters = !showAdvancedFilters">
            {{ showAdvancedFilters ? '收起筛选' : `更多筛选${advancedCount ? ` · ${advancedCount}` : ''}` }}
            <i :class="showAdvancedFilters ? 'i-ri-arrow-up-s-line' : 'i-ri-arrow-down-s-line'"></i>
          </ElButton>
          <ElButton
            native-type="button"
            @click="emit('reset')">
            <i class="i-ri-reset-right-line"></i>
            重置
          </ElButton>
          <ElButton
            v-if="hasExportExcelSlot"
            type="success"
            native-type="button"
            @click="emit('export')">
            <i class="i-ri-download-line"></i>
            导出
          </ElButton>
          <ElButton
            type="primary"
            native-type="button"
            @click="emit('query')">
            <i class="i-ri-search-line"></i>
            搜索
          </ElButton>
        </div>
      </div>

      <div
        v-if="!showAdvancedFilters && advancedCount > 0 && hasActiveFiltersSlot"
        class="query-form__active-filters"
        aria-label="已生效的详细筛选条件">
        <span class="query-form__active-label">已筛选</span>
        <slot name="active-filters"></slot>
      </div>
    </ElForm>
  </div>
</template>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';

.query-form-bar {
  width: 100%;
  box-sizing: border-box;
  flex-shrink: 0;
  overflow: hidden;
  padding: var(--spacing-md) var(--spacing-xl);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.query-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) max-content;
  column-gap: var(--spacing-lg);
}

.query-form__toolbar {
  display: contents;
}

.query-form__fields {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, max(220px, calc((100% - 4 * var(--spacing-md)) / 5))), 1fr));
  align-items: flex-end;
  gap: var(--spacing-md);
  width: 100%;
}

.query-form__fields {
  grid-column: 1;
  min-width: 0;
}

.query-form__advanced {
  display: contents;
}

.query-form__actions {
  display: flex;
  grid-column: 2;
  align-items: center;
  align-self: start;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  flex: 0 0 auto;
  margin-left: auto;
  padding-top: 22px;
}

.query-form__active-filters {
  display: flex;
  grid-column: 1 / -1;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-light);
}

.query-form__active-label {
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}

:deep(.el-form-item) {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
  min-width: 0;
  margin: 0;

  .el-form-item__label {
    justify-content: flex-start;
    text-align: left;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    width: auto !important;
    height: 22px;
    padding: 0;
    color: var(--text-primary);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    line-height: 22px;
    white-space: nowrap;
  }

  .el-form-item__content {
    width: 100%;
    min-width: 0;

    > .el-input,
    > .el-select,
    > .el-date-editor {
      width: 100%;
    }
  }
}

:deep(.query-form-field--date-range) {
  grid-column: span 2;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  box-shadow: none;
  transition: var(--transition-base);

  &:hover {
    border-color: var(--border-dark);
    background: var(--bg-primary);
  }

  &:focus-within {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px var(--primary-lighter);
  }
}

:deep(.el-button) {
  height: 32px;
  margin-left: 0;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);

  i {
    margin-right: var(--spacing-xs);
    font-size: 14px;
  }
}

:deep(.query-form__more) {
  color: var(--primary-color);

  i {
    margin-right: 0;
    margin-left: var(--spacing-xs);
  }
}

.filter-expand-enter-active,
.filter-expand-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.filter-expand-enter-from,
.filter-expand-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (min-width: 769px) and (max-width: 1024px) {
  .query-form {
    grid-template-columns: minmax(0, 1fr);
  }

  .query-form__actions {
    grid-column: 1;
    margin-top: var(--spacing-md);
  }
}

@include mobile {
  .query-form-bar {
    padding: var(--spacing-md);
  }

  .query-form {
    grid-template-columns: minmax(0, 1fr);
  }

  :deep(.el-form-item) {
    width: 100%;
    min-width: 0;
  }

  :deep(.query-form-field--date-range) {
    grid-column: span 1;
  }

  .query-form__actions {
    grid-column: 1;
    width: 100%;
    margin-top: var(--spacing-md);
    margin-left: 0;
    flex-wrap: wrap;

    :deep(.el-button) {
      flex: 1 1 100%;
      min-width: 0;
    }
  }
}

@media (prefers-reduced-motion: reduce) {
  .filter-expand-enter-active,
  .filter-expand-leave-active,
  :deep(.el-input__wrapper),
  :deep(.el-select__wrapper) {
    transition: none;
  }
}
</style>
