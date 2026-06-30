<script setup>
import { ElTabPane, ElTabs } from 'element-plus';
import ProjectTable from './components/ProjectTable.vue';
import ProjectDiskUsage from './components/ProjectDiskUsage.vue';
import { ref } from 'vue';

const activeName = ref('first');
</script>

<template>
  <ElTabs
    v-model="activeName"
    class="flex flex-col h-full">
    <ElTabPane
      label="项目列表"
      name="first"
      class="flex flex-col h-full">
      <ProjectTable></ProjectTable>
    </ElTabPane>
    <ElTabPane
      label="项目存储概览图"
      name="second"
      :lazy="true"
      class="flex flex-col h-full">
      <ProjectDiskUsage></ProjectDiskUsage>
    </ElTabPane>
  </ElTabs>
</template>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';

:deep(.el-tabs) {
  .el-tabs__header {
    margin-bottom: 0;
    border-bottom: 1px solid var(--border-color);
    background: var(--bg-primary);
    padding: 0 var(--spacing-lg);

    .el-tabs__nav-wrap {
      &::after {
        display: none;
      }
    }

    .el-tabs__item {
      height: 48px;
      line-height: 48px;
      font-size: var(--font-size-sm);
      font-weight: var(--font-weight-medium);
      color: var(--text-secondary);
      transition: var(--transition-base);
      padding: 0 var(--spacing-xl);

      &:hover {
        color: var(--primary-color);
      }

      &.is-active {
        color: var(--primary-color);
        font-weight: var(--font-weight-semibold);
      }
    }

    .el-tabs__active-bar {
      background: var(--primary-gradient);
      height: 3px;
      border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    }
  }

  .el-tabs__content {
    flex: 1;
    height: 100%;
    padding: var(--spacing-lg) 0 0;
  }
}
</style>
