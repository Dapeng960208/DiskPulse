<script setup>
import { ElButton, ElTableColumn, ElTag,ElFormItem,ElInput} from 'element-plus';
import { useRouter } from 'vue-router';
import aggregateApi from '@/api/aggregate-api.js';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { useQuery, useQueryParams } from '@/composables/query';
import Progress from '@/components/form/Progress.vue';
import StorageClusterSelect from '@/components/form/StorageClusterSelect.vue';
import { hasRole } from '@/utils/authorization';
import { getStorageResourceNativeType } from '@/utils/storage-resource';
import { useResponsiveTableColumns } from '@/composables/responsive-table-columns';
import StorageTypeTag from '@/components/data/StorageTypeTag.vue';
import TableActionButton from '@/components/basic/TableActionButton.vue';
import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';
import { formatCapacity } from '@/utils/capacity';
const router = useRouter();
const { showCapacityColumns, showSecondaryColumns } = useResponsiveTableColumns();
const { queryParams, reset } = useQueryParams(() => ({
  page: 1,
  size: 20,
  storage_cluster_id: null,
}));

const { result, querying, query } = useQuery(() => aggregateApi.fetch(queryParams.value), {
  content: [],
  totalElements: 0,
});

query();
</script>

<template>
  <div class="user-list-page">
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
        label="容量池名"
        class="query-form-field--wide">
        <ElInput
          v-model="queryParams.nameLike"
          placeholder="根据关键字模糊搜素" />
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
          <AccessibleResourceLink :to="{ name: 'StorageClusterDetail', params: { id: row.storage_cluster?.id } }">{{ row.storage_cluster?.name || '-' }}</AccessibleResourceLink>
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
        label="容量池名"
        align="center"
        prop="name"
        min-width="160"
        show-overflow-tooltip
      >
        <template #default="{ row }"><AccessibleResourceLink :to="{ name: 'AggregateDetail', params: { id: row.id } }">{{ row.name }}</AccessibleResourceLink></template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="原生类型"
        align="center"
        min-width="140">
        <template #default="{ row }">
          {{ getStorageResourceNativeType('aggregate', row) }}
        </template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showCapacityColumns"
        label="限额"
        sortable="custom"
        align="center"
        prop="limit"
        min-width="100"
      >
        <template #default="{ row }">
          <span v-if="row.limit">{{ formatCapacity(row.capacity?.limit, { emptyText: '-' }) }}</span>
          <ElTag
            v-else
            type="danger">无硬限额</ElTag>
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
          <span>{{ formatCapacity(row.capacity?.used, { emptyText: '-' }) }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="使用率(%)"
        align="center"
        prop="use_ratio"
        sortable="custom"
        width="240"
      >
        <template #default="{ row }">
          <Progress
            v-if="row.limit>=0 && row.used>=0 "
            :used="row.used"
            :total="row.limit"
            :show-numbers="false" />
        </template>
      </ElTableColumn>

      <ElTableColumn
        v-if="hasRole('disk-monitor:admin')"
        align="right"
        width="132"
        fixed="right">
        <template #default="{ row }">
          <TableActionButton
            v-if="hasRole('disk-monitor:admin')"
            action="detail"
            @click="router.push({path: `/admin/aggregate/${row.id}`})">
            详情
          </TableActionButton>
        </template>
      </ElTableColumn>
    </DataTable>
  </div>
</template>
