<script setup>
import { ElPagination, ElTable, ElCard } from 'element-plus';
import { computed } from 'vue';

/**
 * @typedef {Object} Pagination 分页参数
 * @property {Number} page 页码
 * @property {Number} pageSize 每页条数
 * @property {Number} total 总数
 * @property {Array<Number>} pageSizes 每页条数选项
 * @property {Boolean} hideOnSinglePage 单页时隐藏分页组件
 * @property {Boolean} showJumper 显示跳页框
 * @property {'top'|'bottom'|'both'} placement 位置
 */

const props = defineProps({
  data: {
    type: Array,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  /**
   * @type import('vue').PropType<Pagination>
   */
  pagination: {
    type: Object,
  },
  striped: {
    type: Boolean,
    default: true,
  },
  density: {
    type: String,
    validator: (value) => ['default', 'compact'].includes(value),
    default: 'default',
  },
  error: {
    type: String,
    default: '',
  },
});
const emit = defineEmits(['update:pagination']);
const paginationLayout = computed(() => {
  let layout = 'total, ->';

  if (props.pagination?.pageSizes) {
    layout += ', sizes';
  }

  if (props.pagination?.showJumper) {
    layout += ', jumper';
  }

  return layout += ', prev, pager, next';
});

defineOptions({
  inheritAttrs: false,
});
function handleSortChange({ column, prop, order }) {
  emit('update:pagination', {
    ...props.pagination,
    prop,
    order,
  });
};
</script>

<template>
  <ElCard
    class="data-table-card h-full"
    :class="{
      'data-table-card--compact': density === 'compact',
      'data-table-card--error': Boolean(error),
    }">
    <ElPagination
      v-if="pagination && ['both', 'top'].includes(props.pagination.placement)"
      class="pagination-top"
      :current-page="pagination.page"
      :page-size="pagination.pageSize"
      :page-sizes="pagination.pageSizes"
      :total="pagination.total"
      :hide-on-single-page="pagination.hideOnSinglePage"
      :layout="paginationLayout"
      @update:current-page="(page) => emit('update:pagination', {
        ...pagination,
        page,
      })"
      @update:page-size="(pageSize) => emit('update:pagination', {
        ...pagination,
        pageSize,
      })"
    />
    <div
      v-if="error"
      class="data-table-error"
      role="alert">
      {{ error }}
    </div>
    <div
      v-else
      class="table-wrapper flex-1">
      <ElTable
        v-loading="loading"
        :data="data"
        :stripe="striped"
        class="h-full"
        scrollbar-always-on
        @sort-change="handleSortChange"
      >
        <slot></slot>
      </ElTable>
    </div>
    <ElPagination
      v-if="pagination && (!props.pagination.placement || ['both', 'bottom'].includes(props.pagination.placement))"
      class="pagination-bottom"
      :current-page="pagination.page"
      :page-size="pagination.pageSize"
      :page-sizes="pagination.pageSizes"
      :total="pagination.total"
      :hide-on-single-page="pagination.hideOnSinglePage"
      :layout="paginationLayout"
      @update:current-page="(page) => emit('update:pagination', {
        ...pagination,
        page,
      })"
      @update:page-size="(pageSize) => emit('update:pagination', {
        ...pagination,
        pageSize,
      })"
    />
  </ElCard>
</template>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';

// 数据表格卡片
.data-table-card {
  margin: 0;
  min-height: 0;
}

:deep(.el-card) {
  @include card-base;
  border: 1px solid var(--border-color);

  .el-card__body {
    height: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: var(--spacing-md) var(--spacing-xl);
    gap: 0;
  }
}

// 分页器 - 顶部
.pagination-top {
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--border-light);
  margin-bottom: var(--spacing-sm);
}

// 分页器 - 底部
.pagination-bottom {
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-light);
  margin-top: var(--spacing-sm);
}

// 表格容器
.table-wrapper {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  border-radius: var(--radius-md);
}

.data-table-error {
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--danger-color);
  background: var(--danger-bg);
  border: 1px solid var(--danger-color);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
}

// 分页器样式
:deep(.el-pagination) {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);

  .el-pagination__total {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    font-weight: var(--font-weight-medium);
  }

  .el-pagination__sizes {
    .el-select {
      .el-input__wrapper {
        border-radius: var(--radius-md);
        box-shadow: none;
        transition: var(--transition-base);
        border: 1px solid var(--border-color);

        &:hover {
          border-color: var(--primary-color);
        }
      }
    }
  }

  .el-pager {
    li {
      min-width: 30px;
      height: 30px;
      line-height: 30px;
      border-radius: var(--radius-sm);
      font-size: var(--font-size-sm);
      color: var(--text-secondary);
      transition: var(--transition-base);

      &:hover {
        background: var(--bg-hover);
        color: var(--primary-color);
      }

      &.is-active {
        background: var(--primary-gradient);
        color: white;
        font-weight: var(--font-weight-medium);
      }
    }
  }

  .btn-prev,
  .btn-next {
    width: 30px;
    height: 30px;
    border-radius: var(--radius-sm);
    background: var(--bg-secondary);
    transition: var(--transition-base);

    &:hover:not(:disabled) {
      background: var(--bg-hover);
      color: var(--primary-color);
    }

    &:disabled {
      color: var(--text-disabled);
      cursor: not-allowed;
    }
  }

  .el-pagination__jump {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);

    .el-input__wrapper {
      border-radius: var(--radius-md);
      box-shadow: none;
      border: 1px solid var(--border-color);
    }
  }
}

// 表格样式
:deep(.el-table) {
  border-radius: var(--radius-md);
  overflow: hidden;
  font-size: var(--font-size-sm);

  .el-table__header-wrapper {
    .el-table__header {
      thead {
        tr {
          th {
            background: var(--bg-secondary);
            color: var(--text-primary);
            font-weight: var(--font-weight-semibold);
            font-size: var(--font-size-sm);
            border-bottom: 2px solid var(--border-color);
            padding: var(--spacing-sm) 0;

            .cell {
              padding: 0 var(--spacing-md);
            }
          }
        }
      }
    }
  }

  .el-table__body-wrapper {
    .el-table__body {
      tbody {
        tr {
          transition: var(--transition-base);

          &:hover {
            background: var(--bg-hover) !important;
          }

          td {
            border-bottom: 1px solid var(--border-light);
            padding: var(--spacing-sm) 0;
            color: var(--text-secondary);

            .cell {
              padding: 0 var(--spacing-md);
            }
          }

          &.el-table__row--striped {
            background: var(--bg-secondary);
          }
        }
      }
    }
  }

  // 空状态
  .el-table__empty-block {
    padding: var(--spacing-3xl) 0;

    .el-table__empty-text {
      color: var(--text-tertiary);
      font-size: var(--font-size-sm);
    }
  }

  // 加载状态
  .el-loading-mask {
    background: rgba(255, 255, 255, 0.8);

    html.dark & {
      background: rgba(15, 23, 42, 0.8);
    }
  }
}

// 表格内按钮样式
:deep(.el-button) {
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  transition: var(--transition-base);

  &.el-button--small {
    padding: 4px 10px;
    height: 28px;
  }

  &.is-plain {
    &:hover {
      background: var(--bg-hover);
      border-color: var(--primary-color);
      color: var(--primary-color);
    }
  }
}

.data-table-card--compact {
  :deep(.el-card__body) {
    padding: var(--spacing-sm) var(--spacing-lg);
  }

  :deep(.el-table) {
    .el-table__header-wrapper th,
    .el-table__body-wrapper td {
      padding: var(--spacing-xs) 0;
    }
  }
}
</style>
