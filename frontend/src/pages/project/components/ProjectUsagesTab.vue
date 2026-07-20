<script setup>
import { reactive, ref } from 'vue';
import { ElTableColumn } from 'element-plus';
import storageUsageApi from '@/api/storage-usage-api.js';
import DataTable from '@/components/data/DataTable.vue';
import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';
import Progress from '@/components/form/Progress.vue';
import { formatQuotaLimit } from '@/utils/quota';

const props = defineProps({
  projectId: {
    type: Number,
    required: true,
  },
});

const usages = ref([]);
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
    const result = await storageUsageApi.fetch({
      project_id: props.projectId,
      page: pagination.page,
      size: pagination.pageSize,
    });
    if (requestId !== latestRequestId) return;
    usages.value = result.content || [];
    pagination.total = Number(result.total) || 0;
  } catch {
    if (requestId !== latestRequestId) return;
    usages.value = [];
    pagination.total = 0;
    error.value = '加载用户目录失败，请稍后重试';
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
    :data="usages"
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
      label="用户"
      min-width="150">
      <template #default="{ row }">{{ row.user?.rd_username || row.user?.username || '-' }}</template>
    </ElTableColumn>
    <ElTableColumn
      label="Linux 路径"
      min-width="240"
      show-overflow-tooltip>
      <template #default="{ row }">
        <AccessibleResourceLink :to="{ name: 'UsagesDetail', params: { id: row.id } }">{{ row.linux_path }}</AccessibleResourceLink>
      </template>
    </ElTableColumn>
    <ElTableColumn
      label="项目组"
      min-width="150">
      <template #default="{ row }">{{ row.group?.name || '-' }}</template>
    </ElTableColumn>
    <ElTableColumn
      label="存储集群"
      min-width="150">
      <template #default="{ row }">{{ row.storage_cluster?.name || '-' }}</template>
    </ElTableColumn>
    <ElTableColumn
      label="使用量"
      width="110">
      <template #default="{ row }">{{ formatQuotaLimit(row.used, { emptyText: '-' }) }}</template>
    </ElTableColumn>
    <ElTableColumn
      label="限额"
      width="110">
      <template #default="{ row }">{{ formatQuotaLimit(row.limit) }}</template>
    </ElTableColumn>
    <ElTableColumn
      label="使用率"
      width="220">
      <template #default="{ row }"><Progress
        v-if="row.used != null && row.limit > 0"
        :used="row.used"
        :total="row.limit"
        :show-numbers="false" /></template>
    </ElTableColumn>
  </DataTable>
</template>
