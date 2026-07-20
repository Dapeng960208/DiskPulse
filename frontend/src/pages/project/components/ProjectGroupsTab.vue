<script setup>
import { reactive, ref } from 'vue';
import { ElTableColumn } from 'element-plus';
import groupApi from '@/api/group-api.js';
import DataTable from '@/components/data/DataTable.vue';
import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';
import StorageTypeTag from '@/components/data/StorageTypeTag.vue';
import { formatStorageTargetType } from '@/utils/storage-resource';

const props = defineProps({
  projectId: {
    type: Number,
    required: true,
  },
});

const groups = ref([]);
const loading = ref(false);
const error = ref('');
const pagination = reactive({ page: 1, pageSize: 20, total: 0 });
let latestRequestId = 0;

async function query() {
  if (!props.projectId) return;
  const requestId = ++latestRequestId;
  loading.value = true;
  error.value = '';
  try {
    const result = await groupApi.fetch({
      project_id: props.projectId,
      page: pagination.page,
      size: pagination.pageSize,
    });
    if (requestId !== latestRequestId) return;
    groups.value = result.content || [];
    pagination.total = Number(result.total) || 0;
  } catch {
    if (requestId !== latestRequestId) return;
    groups.value = [];
    pagination.total = 0;
    error.value = '加载项目组失败，请稍后重试';
  } finally {
    if (requestId === latestRequestId) loading.value = false;
  }
}

function updatePagination(next) {
  pagination.page = next.page;
  pagination.pageSize = next.pageSize;
  query();
}

query();
</script>

<template>
  <DataTable
    :data="groups"
    :loading="loading"
    :error="error"
    :pagination="{
      page: pagination.page,
      pageSize: pagination.pageSize,
      total: pagination.total,
      pageSizes: [20, 50, 100],
      hideOnSinglePage: true,
      showJumper: true,
    }"
    @update:pagination="updatePagination">
    <ElTableColumn
      label="项目组"
      min-width="160"
      show-overflow-tooltip>
      <template #default="{ row }">
        <AccessibleResourceLink :to="{ name: 'GroupDetail', params: { id: row.id } }">{{ row.name || '-' }}</AccessibleResourceLink>
      </template>
    </ElTableColumn>
    <ElTableColumn
      label="项目组标签"
      min-width="140">
      <template #default="{ row }">{{ row.group_tag?.name || '-' }}</template>
    </ElTableColumn>
    <ElTableColumn
      label="存储集群"
      min-width="150">
      <template #default="{ row }">{{ row.storage_cluster?.name || '-' }}</template>
    </ElTableColumn>
    <ElTableColumn
      label="存储类型"
      width="120">
      <template #default="{ row }"><StorageTypeTag :value="row.storage_cluster?.storage_type" /></template>
    </ElTableColumn>
    <ElTableColumn
      label="存储目标"
      min-width="200">
      <template #default="{ row }">{{ formatStorageTargetType(row.storage_target?.type) }} / {{ row.storage_target?.name || '-' }}</template>
    </ElTableColumn>
    <ElTableColumn
      label="Linux 路径"
      prop="linux_path"
      min-width="220"
      show-overflow-tooltip />
  </DataTable>
</template>
