<script setup>
import { ElButton,  ElTableColumn, ElTag,ElFormItem,ElInput } from 'element-plus';
import { RouterLink, useRouter } from 'vue-router';
import volumeApi from '@/api/volume-api.js';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { hasRole } from '@/utils/authorization';
import { useQuery, useQueryParams } from '@/composables/query';
import Progress from '@/components/form/Progress.vue'
const router = useRouter();

const { queryParams, reset } = useQueryParams(() => ({
  page: 1,
  size: 20,
  project_id: null,
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
      <ElFormItem label="Volume名">
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
        label="存储集群"
        align="center"
        prop="storageCluster.name"
        min-width="100"
      >
        <template #default="{ row }">
          <span>{{ row.storage_cluster?.name || '-' }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="Volume名"
        align="center"
        prop="name"
        min-width="120"
      />
      <ElTableColumn
        label="vserver"
        align="center"
        sortable
        prop="vserver"
        min-width="80"
      >
      </ElTableColumn>

      <ElTableColumn
        label="聚合"
        align="center"
        prop="aggregate"
        min-width="120"
      />
      <ElTableColumn
        label="类型"
        align="center"
        prop="type"
        min-width="50"
      />
      <ElTableColumn
        label="状态"
        align="center"
        prop="state"
        min-width="50"
      />
      <ElTableColumn
        label="状态"
        align="center"
        prop="state"
        min-width="50"
      />
      <ElTableColumn
        label="限额"
        sortable="custom"
        align="center"
        prop="limit"
        min-width="50"
      >
        <template #default="{ row }">
          <span v-if="row.limit">{{ row.limit>=1024 ? `${(row.limit/1024).toFixed(1)} T`: `${row.limit} G` }}</span>
          <ElTag
            v-else
            type="danger">无限额</ElTag>
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
        label="使用量"
        sortable="custom"
        align="center"
        prop="used"
        min-width="50"
      >
        <template #default="{ row }">
          <span>{{ row.used>=1024 ? `${(row.used/1024).toFixed(1)} T`: `${row.used} G` }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="利用率(%)"
        align="center"
        prop="use_ratio"
        sortable="custom"
        width="400"
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
        min-width="120">
        <template #default="{ row }">
          <ElButton
            v-if="hasRole('disk-monitor:admin')"
            size="small"
            plain
            @click="router.push({path: `/storage/volume/${row.id}`})">
            详情
          </ElButton>
        </template>
      </ElTableColumn>
    </DataTable>
  </div></template>
