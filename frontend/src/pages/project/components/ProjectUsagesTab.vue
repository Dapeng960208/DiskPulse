<script setup>
import { reactive, ref } from 'vue';
import { ElFormItem, ElInput, ElTableColumn, ElTag } from 'element-plus';
import storageUsageApi from '@/api/storage-usage-api.js';
import DataTable from '@/components/data/DataTable.vue';
import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';
import GroupSelect from '@/components/form/GroupSelect.vue';
import GroupTagSelect from '@/components/form/GroupTagSelect.vue';
import Progress from '@/components/form/Progress.vue';
import QueryForm from '@/components/form/QueryForm.vue';
import RdUserSelect from '@/components/form/RdUserSelect.vue';
import StorageClusterSelect from '@/components/form/StorageClusterSelect.vue';
import { canRenderQuotaProgress, formatQuotaLimit } from '@/utils/quota';

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
const filters = reactive({
  user_id: null,
  group_tag_id: null,
  group_id: null,
  storage_cluster_id: null,
  nameLike: '',
});
let latestRequestId = 0;

function requestParams() {
  const params = {
    project_id: props.projectId,
    page: pagination.page,
    size: pagination.pageSize,
  };
  if (filters.user_id) params.user_id = filters.user_id;
  if (filters.group_tag_id) params.group_tag_id = filters.group_tag_id;
  if (filters.group_id) params.group_id = filters.group_id;
  if (filters.storage_cluster_id) params.storage_cluster_id = filters.storage_cluster_id;
  if (filters.nameLike.trim()) params.nameLike = filters.nameLike.trim();
  return params;
}

async function query() {
  if (!props.projectId) return;
  const requestId = ++latestRequestId;
  loading.value = true;
  error.value = '';
  try {
    const result = await storageUsageApi.fetch(requestParams());
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

function queryWithFilters() {
  pagination.page = 1;
  query();
}

function changeGroupTag(groupTagId) {
  filters.group_tag_id = groupTagId;
  filters.group_id = null;
}

function resetFilters() {
  Object.assign(filters, {
    user_id: null,
    group_tag_id: null,
    group_id: null,
    storage_cluster_id: null,
    nameLike: '',
  });
  queryWithFilters();
}

function updatePagination(next) {
  pagination.page = next.page;
  pagination.pageSize = next.pageSize;
  query();
}

query();
</script>

<template>
  <section class="project-usages-tab">
    <QueryForm
      @query="queryWithFilters"
      @reset="resetFilters">
      <ElFormItem label="研发用户名">
        <RdUserSelect
          v-model="filters.user_id"
          :multiple="false"
          clearable />
      </ElFormItem>
      <ElFormItem label="存储集群">
        <StorageClusterSelect
          v-model="filters.storage_cluster_id"
          :multiple="false"
          clearable />
      </ElFormItem>
      <template #advanced>
        <ElFormItem label="项目组标签">
          <GroupTagSelect
            :model-value="filters.group_tag_id"
            clearable
            @update:model-value="changeGroupTag" />
        </ElFormItem>
        <ElFormItem
          label="Linux 目录"
          class="query-form-field--wide">
          <ElInput
            v-model="filters.nameLike"
            clearable
            placeholder="根据关键字模糊搜索" />
        </ElFormItem>
        <ElFormItem label="项目组">
          <GroupSelect
            v-model="filters.group_id"
            :project-id="projectId"
            :group-tag-id="filters.group_tag_id"
            :multiple="false"
            clearable />
        </ElFormItem>
      </template>
    </QueryForm>
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
        label="研发用户名"
        min-width="140"
        show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ row.user?.rd_username || row.user?.username || '-' }}</span>
          <ElTag
            v-if="row.user?.user_type === 0"
            type="danger"
            class="ml-2.5">离职账户</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="项目组标签"
        min-width="120">
        <template #default="{ row }">{{ row.group_tag?.name || '-' }}</template>
      </ElTableColumn>
      <ElTableColumn
        label="项目组"
        min-width="150">
        <template #default="{ row }">
          <AccessibleResourceLink
            v-if="row.group"
            :to="{ name: 'GroupDetail', params: { id: row.group.id } }">{{ row.group.name }}</AccessibleResourceLink>
          <ElTag v-else>默认</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="存储集群"
        min-width="150">
        <template #default="{ row }">
          <AccessibleResourceLink :to="{ name: 'StorageClusterDetail', params: { id: row.storage_cluster?.id } }">{{ row.storage_cluster?.name || '-' }}</AccessibleResourceLink>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="Linux 路径"
        prop="linux_path"
        min-width="240"
        show-overflow-tooltip>
        <template #default="{ row }">
          <AccessibleResourceLink :to="{ name: 'UsagesDetail', params: { id: row.id } }">{{ row.linux_path || '-' }}</AccessibleResourceLink>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="硬限额"
        min-width="110">
        <template #default="{ row }">
          <span v-if="row.limit">{{ formatQuotaLimit(row.capacity?.limit ?? row.limit) }}</span>
          <ElTag
            v-else
            type="danger">无硬限额</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="软限额"
        min-width="110">
        <template #default="{ row }">
          <span v-if="row.soft_limit">{{ formatQuotaLimit(row.capacity?.soft_limit ?? row.soft_limit) }}</span>
          <ElTag
            v-else
            type="warning">无软限额</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="使用量"
        min-width="110">
        <template #default="{ row }">{{ formatQuotaLimit(row.capacity?.used ?? row.used, { emptyText: '-' }) }}</template>
      </ElTableColumn>
      <ElTableColumn
        label="硬限额使用率(%)"
        min-width="220">
        <template #default="{ row }">
          <Progress
            v-if="canRenderQuotaProgress({ used: row.used, total: row.limit })"
            :used="row.used"
            :total="row.limit"
            :show-numbers="false" />
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="软限额使用率(%)"
        min-width="220">
        <template #default="{ row }">
          <Progress
            v-if="canRenderQuotaProgress({ used: row.used, total: row.soft_limit })"
            :used="row.used"
            :total="row.soft_limit"
            :show-numbers="false" />
          <ElTag
            v-else
            type="warning">无软限额</ElTag>
        </template>
      </ElTableColumn>
    </DataTable>
  </section>
</template>

<style scoped>
.project-usages-tab {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  gap: var(--spacing-md);
}

.project-usages-tab :deep(.data-table-card) {
  flex: 1 1 auto;
  min-height: 0;
  height: auto;
}
</style>
