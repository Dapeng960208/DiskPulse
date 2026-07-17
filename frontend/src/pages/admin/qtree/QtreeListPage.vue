<script setup>
import { ElButton, ElFormItem, ElInput, ElMessage, ElTableColumn, ElTag } from 'element-plus';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import qtreeApi from '@/api/qtree-api.js';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { hasRole } from '@/utils/authorization';
import { useQuery, useQueryParams } from '@/composables/query';
import Progress from '@/components/form/Progress.vue'
import VolumeSelect from '@/components/form/VolumeSelect.vue'
import StorageClusterSelect from '@/components/form/StorageClusterSelect.vue';
import storageClusterApi from '@/api/storage-cluster-api';
import { canRenderQuotaProgress, formatQuotaLimit } from '@/utils/quota';
import { useResponsiveTableColumns } from '@/composables/responsive-table-columns';
const router = useRouter();
const selectedCluster = ref(null);
const { showCapacityColumns, showSecondaryColumns } = useResponsiveTableColumns();
const { queryParams, reset } = useQueryParams(() => ({
  page: 1,
  size: 20,
  storage_cluster_id: null,
}));

const { result, querying, query } = useQuery(() => qtreeApi.fetch(queryParams.value), {
  content: [],
  totalElements: 0,
});

async function changeCluster(clusterId) {
  queryParams.value.storage_cluster_id = clusterId;
  delete queryParams.value.volume_id;
  selectedCluster.value = clusterId ? await storageClusterApi.fetchById(clusterId) : null;
  if (selectedCluster.value?.storage_type === 'isilon') {
    ElMessage.warning('Isilon 不支持 Qtree');
  }
}

function runQuery() {
  if (selectedCluster.value?.storage_type === 'isilon') {
    ElMessage.warning('Isilon 不支持 Qtree');
    return;
  }
  queryParams.value.page = 1;
  query();
}

function resetQuery() {
  selectedCluster.value = null;
  reset();
  query();
}

query();
</script>

<template>
  <div class="qtree-list-page">
    <FilterForm
      @query="runQuery"
      @reset="resetQuery"
    >
      <ElFormItem
        label="存储集群"
        class="form-item-center">
        <StorageClusterSelect
          :model-value="queryParams.storage_cluster_id"
          :clearable="true"
          @update:model-value="changeCluster" />
      </ElFormItem>
      <ElFormItem
        label="Qtree（NetApp）"
        class="query-form-field--wide">
        <ElInput
          v-model="queryParams.nameLike"
          placeholder="根据 Qtree（NetApp）搜索" />
      </ElFormItem>
      <ElFormItem label="所属存储空间">
        <VolumeSelect
          v-model="queryParams.volume_id"
          :storage-cluster-id="queryParams.storage_cluster_id"
          :multiple="false"
          :clearable="true" />
      </ElFormItem>
    </FilterForm>
    <DataTable
      :pagination="{
        page: queryParams.page,
        pageSize: queryParams.size,
        total: result.total,
        pageSizes:[20,50,100,200,500],
        hideOnSinglePage:true,
        showJumper:true
      }"
      :loading="querying"
      :data="result.content"
      @update:pagination="({ page, pageSize, prop, order }) => {
        queryParams.page = page;
        queryParams.size = pageSize;
        queryParams.prop = prop ?? queryParams.prop;
        queryParams.order = order ?? queryParams.order;
        query();
      }"
    >
      <ElTableColumn
        v-if="showCapacityColumns"
        label="存储集群"
        align="center"
        prop="storageCluster.name"
        min-width="140"
      >
        <template #default="{ row }">
          <span>{{ row.storage_cluster?.name || '-' }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="Qtree（NetApp）名"
        align="center"
        prop="name"
        min-width="180"
        show-overflow-tooltip
      />
      <ElTableColumn
        v-if="showCapacityColumns"
        label="所属存储空间"
        align="center"
        min-width="160"
      >
        <template #default="{ row }">
          <span>{{ row.volume.name }}</span>
        </template>
      </ElTableColumn>

      <ElTableColumn
        v-if="showSecondaryColumns"
        label="style"
        align="center"
        prop="style"
        min-width="120"
      />
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="oplocks"
        align="center"
        prop="oplocks"
        min-width="50"
      />
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="状态"
        align="center"
        prop="status"
        min-width="90"
      />
      <ElTableColumn
        v-if="showCapacityColumns"
        label="硬限额"
        sortable="custom"
        align="center"
        prop="limit"
        min-width="100"
      >
        <template #default="{ row }">
          <span v-if="row.limit">{{ formatQuotaLimit(row.limit) }}</span>
          <ElTag
            v-else
            type="danger">无硬限额</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showCapacityColumns"
        label="软限额"
        sortable="custom"
        align="center"
        prop="soft_limit"
        min-width="100"
      >
        <template #default="{ row }">
          <span v-if="row.soft_limit">{{ formatQuotaLimit(row.soft_limit, { emptyText: '无软限额' }) }}</span>
          <ElTag
            v-else
            type="warning">无软限额</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showCapacityColumns"
        label="使用量"
        sortable="custom"
        align="center"
        prop="used"
        min-width="100"
      >
        <template #default="{ row }">
          <span>{{ row.used>=1024 ? `${(row.used/1024).toFixed(1)} T`: `${row.used} G` }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="硬限额使用率(%)"
        align="center"
        prop="use_ratio"
        sortable="custom"
        width="240"
      >
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
        align="center"
        prop="soft_use_ratio"
        sortable="custom"
        width="240"
      >
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
      <ElTableColumn
        v-if="hasRole('disk-monitor:admin')"
        align="right"
        width="132">
        <template #default="{ row }">
          <ElButton
            v-if="hasRole('disk-monitor:admin')"
            size="small"
            plain
            @click="router.push({path: `/admin/qtree/${row.id}`})">
            详情
          </ElButton>
        </template>
      </ElTableColumn>
    </DataTable>
  </div></template>
