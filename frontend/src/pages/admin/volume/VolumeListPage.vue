<script setup>
import { ElButton,  ElTableColumn, ElTag,ElFormItem,ElInput } from 'element-plus';
import { RouterLink, useRouter } from 'vue-router';
import volumeApi from '@/api/volume-api.js';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { hasRole } from '@/utils/authorization';
import { useQuery, useQueryParams } from '@/composables/query';
import Progress from '@/components/form/Progress.vue'
import StorageClusterSelect from '@/components/form/StorageClusterSelect.vue';
import { canRenderQuotaProgress, formatQuotaLimit } from '@/utils/quota';
import { getStorageResourceNativeType } from '@/utils/storage-resource';
import { useResponsiveTableColumns } from '@/composables/responsive-table-columns';
import StorageTypeTag from '@/components/data/StorageTypeTag.vue';
const router = useRouter();
const { showCapacityColumns, showSecondaryColumns } = useResponsiveTableColumns();

const { queryParams, reset } = useQueryParams(() => ({
  page: 1,
  size: 20,
  storage_cluster_id: null,
}));

const { result, querying, query } = useQuery(() => volumeApi.fetch(queryParams.value), {
  content: [],
  totalElements: 0,
});

query();
</script>

<template>
  <div class="volume-list-page">
    <FilterForm
      @query="{
        queryParams.page = 1;
        query();
      }"
      @reset="{
        reset();
        query();
      }"
    >
      <ElFormItem
        label="存储集群"
        class="form-item-center">
        <StorageClusterSelect
          v-model="queryParams.storage_cluster_id"
          :clearable="true" />
      </ElFormItem>
      <ElFormItem
        label="存储空间名"
        class="query-form-field--wide">
        <ElInput
          v-model="queryParams.nameLike"
          placeholder="根据名称或路径模糊搜索" />
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
        v-if="showCapacityColumns"
        label="存储类型"
        align="center"
        min-width="90">
        <template #default="{ row }">
          <StorageTypeTag :value="row.storage_cluster?.storage_type" />
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="存储空间名"
        align="center"
        prop="name"
        min-width="180"
        show-overflow-tooltip
      />
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="服务域（SVM / Access Zone）"
        align="center"
        sortable
        prop="vserver"
        min-width="160"
      >
      </ElTableColumn>

      <ElTableColumn
        v-if="showCapacityColumns"
        label="所属容量池"
        align="center"
        prop="aggregate"
        min-width="120"
      />
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="原生类型"
        align="center"
        min-width="150">
        <template #default="{ row }">
          {{ getStorageResourceNativeType('volume', row) }}
        </template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showCapacityColumns"
        label="状态"
        align="center"
        prop="state"
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
      <!-- <ElTableColumn
        label="分配"
        sortable="custom"
        align="center"
        prop="allocated"
        min-width="50"
      >
        <template #default="{ row }">
          <ElTag :type="row.allocated>row.limit?'danger':'success'">
            <span>{{ row.allocated>=1024 ? `${(row.allocated/1024).toFixed(1)} T`: `${row.allocated} G` }}</span>
          </ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="分配比"
        align="center"
        min-width="50"
      >
        <template #default="{ row }">
          <span>{{ (row.allocated*100/row.limit).toFixed(2) }} %</span>
        </template>
      </ElTableColumn> -->
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
            @click="router.push({path: `/admin/volume/${row.id}`})">
            详情
          </ElButton>
        </template>
      </ElTableColumn>
    </DataTable>
  </div></template>
