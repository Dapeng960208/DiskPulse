<script setup>
import {
  ElAlert,
  ElButton,
  ElEmpty,
  ElMessage,
  ElMessageBox,
  ElTableColumn,
  ElTag,
} from 'element-plus';
import { ref } from 'vue';
import projectStorageEnvironmentApi from '@/api/project-storage-environment-api';
import DataTable from '@/components/data/DataTable.vue';
import ProjectStorageEnvironmentFormDialog from './ProjectStorageEnvironmentFormDialog.vue';

const props = defineProps({
  projectId: {
    type: Number,
    required: true,
  },
});

const formDialogRef = ref();
const queryParams = ref({ page: 1, size: 20 });
const result = ref({ content: [], total: 0 });
const querying = ref(false);
const loadFailed = ref(false);

async function query() {
  querying.value = true;
  loadFailed.value = false;
  try {
    result.value = await projectStorageEnvironmentApi.fetchByProject(
      props.projectId,
      queryParams.value,
    );
  } catch {
    result.value = { content: [], total: 0 };
    loadFailed.value = true;
  } finally {
    querying.value = false;
  }
}

function updatePagination({ page, pageSize }) {
  queryParams.value.page = page;
  queryParams.value.size = pageSize;
  query();
}

async function confirmDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除存储环境「${row.name}」？此操作不可撤销。`,
      '提示',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    );
    await projectStorageEnvironmentApi.deleteById(row.id);
    ElMessage.success('删除成功');
    await query();
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return;
    }
    if (error?.response?.status === 409) {
      ElMessage.error('该存储环境已关联项目组，无法删除');
      return;
    }
    ElMessage.error('删除存储环境失败，请稍后重试');
  }
}

query();
</script>

<template>
  <div class="project-storage-environment-table">
    <div class="mb-3 flex justify-end">
      <ElButton
        type="primary"
        @click="formDialogRef.create()">
        新增存储环境
      </ElButton>
    </div>

    <ElAlert
      v-if="loadFailed"
      title="加载存储环境失败，请稍后重试"
      type="error"
      :closable="false" />
    <ElEmpty
      v-else-if="!querying && result.content.length === 0"
      description="暂无存储环境" />
    <DataTable
      v-else
      :loading="querying"
      :data="result.content"
      :pagination="{
        page: queryParams.page,
        pageSize: queryParams.size,
        total: result.total,
        pageSizes: [10, 20, 50, 100],
        hideOnSinglePage: true,
        showJumper: true,
      }"
      @update:pagination="updatePagination">
      <ElTableColumn
        label="环境名称"
        prop="name"
        min-width="160" />
      <ElTableColumn
        label="存储集群"
        min-width="160">
        <template #default="{ row }">
          {{ row.storage_cluster?.name || '-' }}
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="存储类型"
        min-width="110">
        <template #default="{ row }">
          {{ row.storage_cluster?.storage_type || '-' }}
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="描述"
        prop="description"
        min-width="180"
        show-overflow-tooltip />
      <ElTableColumn
        label="状态"
        min-width="100">
        <template #default="{ row }">
          <ElTag :type="row.is_active ? 'success' : 'info'">
            {{ row.is_active ? '启用' : '停用' }}
          </ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="采集状态"
        prop="collection_status"
        min-width="110" />
      <ElTableColumn
        label="操作"
        align="right"
        min-width="140">
        <template #default="{ row }">
          <ElButton
            type="primary"
            link
            @click="formDialogRef.edit(row)">
            编辑
          </ElButton>
          <ElButton
            type="danger"
            link
            @click="confirmDelete(row)">
            删除
          </ElButton>
        </template>
      </ElTableColumn>
    </DataTable>

    <ProjectStorageEnvironmentFormDialog
      ref="formDialogRef"
      :project-id="projectId"
      @submitted="query" />
  </div>
</template>
