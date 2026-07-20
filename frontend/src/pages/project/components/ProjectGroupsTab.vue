<script setup>
import { reactive, ref } from 'vue';
import { ElFormItem, ElInput, ElTableColumn } from 'element-plus';
import groupApi from '@/api/group-api.js';
import DataTable from '@/components/data/DataTable.vue';
import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';
import StorageTypeTag from '@/components/data/StorageTypeTag.vue';
import QueryForm from '@/components/form/QueryForm.vue';
import GroupTagSelect from '@/components/form/GroupTagSelect.vue';
import QtreeSelect from '@/components/form/QtreeSelect.vue';
import StorageClusterSelect from '@/components/form/StorageClusterSelect.vue';
import VolumeSelect from '@/components/form/VolumeSelect.vue';
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
const filters = reactive({
  nameLike: '',
  group_tag_id: null,
  storage_cluster_id: null,
  volume_id: null,
  qtree_id: null,
});
let latestRequestId = 0;

function requestParams() {
  const params = {
    project_id: props.projectId,
    page: pagination.page,
    size: pagination.pageSize,
  };
  if (filters.nameLike.trim()) params.nameLike = filters.nameLike.trim();
  if (filters.group_tag_id) params.group_tag_id = filters.group_tag_id;
  if (filters.storage_cluster_id) params.storage_cluster_id = filters.storage_cluster_id;
  if (filters.volume_id) params.volume_id = filters.volume_id;
  if (filters.qtree_id) params.qtree_id = filters.qtree_id;
  return params;
}

async function query() {
  if (!props.projectId) return;
  const requestId = ++latestRequestId;
  loading.value = true;
  error.value = '';
  try {
    const result = await groupApi.fetch(requestParams());
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

function queryWithFilters() {
  pagination.page = 1;
  query();
}

function resetFilters() {
  Object.assign(filters, {
    nameLike: '',
    group_tag_id: null,
    storage_cluster_id: null,
    volume_id: null,
    qtree_id: null,
  });
  queryWithFilters();
}

function changeStorageCluster(clusterId) {
  filters.storage_cluster_id = clusterId;
  filters.volume_id = null;
  filters.qtree_id = null;
}

function changeVolume(volumeId) {
  filters.volume_id = volumeId;
  filters.qtree_id = null;
}

function changeQtree(qtreeId) {
  filters.qtree_id = qtreeId;
  filters.volume_id = null;
}

function updatePagination(next) {
  pagination.page = next.page;
  pagination.pageSize = next.pageSize;
  query();
}

query();
</script>

<template>
  <section class="project-groups-tab">
    <QueryForm
      @query="queryWithFilters"
      @reset="resetFilters">
      <ElFormItem
        label="项目组名称"
        class="query-form-field--wide">
        <ElInput
          v-model="filters.nameLike"
          clearable
          placeholder="根据项目组名模糊搜索" />
      </ElFormItem>
      <ElFormItem label="存储集群">
        <StorageClusterSelect
          :model-value="filters.storage_cluster_id"
          clearable
          @update:model-value="changeStorageCluster" />
      </ElFormItem>
      <template #advanced>
        <ElFormItem label="项目组标签">
          <GroupTagSelect
            v-model="filters.group_tag_id"
            clearable />
        </ElFormItem>
        <ElFormItem label="关联存储空间">
          <VolumeSelect
            :model-value="filters.volume_id"
            :storage-cluster-id="filters.storage_cluster_id"
            clearable
            @update:model-value="changeVolume" />
        </ElFormItem>
        <ElFormItem label="关联 Qtree（NetApp）">
          <QtreeSelect
            :model-value="filters.qtree_id"
            :storage-cluster-id="filters.storage_cluster_id"
            clearable
            @update:model-value="changeQtree" />
        </ElFormItem>
      </template>
    </QueryForm>
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
  </section>
</template>
