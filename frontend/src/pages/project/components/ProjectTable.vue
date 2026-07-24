<script setup>
import { ElButton, ElFormItem, ElInput, ElTag, ElTableColumn,ElTabPane,ElTabs } from 'element-plus';
import { computed, ref } from 'vue';
import {  useRouter } from 'vue-router';
import projectApi from '@/api/project-api';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { useQuery, useQueryParams } from '@/composables/query';
import { hasRole } from '@/utils/authorization';
import Progress from '@/components/form/Progress.vue';
import ProjectFormDialog from './ProjectFormDialog.vue';
import UserAvatar from '@/components/data/UserAvatar.vue'
import { useResponsiveTableColumns } from '@/composables/responsive-table-columns';
import StorageTypeTag from '@/components/data/StorageTypeTag.vue';
import TableActionButton from '@/components/basic/TableActionButton.vue';
import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';
import { formatCapacity } from '@/utils/capacity';
const projectFormDialogRef = ref();
const { showCapacityColumns, showSecondaryColumns } = useResponsiveTableColumns();
const { queryParams, reset } = useQueryParams(() => ({
  page: 1,
  size: 20,
  nameLike: null,
}));
const router = useRouter();
const { result,querying,query } = useQuery(() => projectApi.fetch(queryParams.value), {
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
        label="项目名"
        class="query-form-field--wide">
        <ElInput
          v-model="queryParams.nameLike"
          placeholder="根据项目名搜索" />
      </ElFormItem>
    </FilterForm>
    <DataTable
      :pagination="{
        page:queryParams.page,
        pageSize: queryParams.size,
        total: result.total,
        pageSizes:[20,50,100,200,500],
        hideOnSinglePage:true,
        showJumper:true
      }"
      :loading="querying"
      :data="result.content"
      @update:pagination="({ page, pageSize }) => {
        queryParams.page = page;
        queryParams.size = pageSize;
        query();
      }"
    >
      <ElTableColumn
        label="项目"
        prop="name"
        align="center"
        sortable
        min-width="160"
        show-overflow-tooltip>
        <template #default="{ row }"><AccessibleResourceLink :to="{ name: 'ProjectDetail', params: { id: row.id } }">{{ row.name }}</AccessibleResourceLink></template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="存储集群"
        align="center"
        min-width="140">
        <template #default="{ row }">
          <template v-if="row.storage_clusters?.length">
            <div
              v-for="cluster in row.storage_clusters"
              :key="cluster.id"><AccessibleResourceLink :to="{ name: 'StorageClusterDetail', params: { id: cluster.id } }">{{ cluster.name }}</AccessibleResourceLink></div>
          </template>
          <span v-else>-</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="存储类型"
        align="center"
        min-width="90">
        <template #default="{ row }">
          <template v-if="row.storage_clusters?.length">
            <div
              v-for="cluster in row.storage_clusters"
              :key="cluster.id">
              <StorageTypeTag :value="cluster.storage_type" />
            </div>
          </template>
          <span v-else>-</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showCapacityColumns"
        label="项目负责人"
        align="center"
        sortable
        min-width="160"
      >
        <template #default="{ row }">
          <div style="display: flex; align-items: center; justify-content: center;">
            <UserAvatar
              v-if="row.in_charge_user && row.in_charge_user.avatar_url"
              :src="row.in_charge_user.avatar_url" />
            <span style="margin-left: 8px;">{{ row?.in_charge_user?.rd_username }} {{ row?.in_charge_user?.username }}</span>
          </div>
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
        align="right"
        width="132"
        fixed="right">
        <template #header>
          <TableActionButton
            action="create"
            @click="projectFormDialogRef.edit()">
            添加项目
          </TableActionButton>
        </template>
        <template #default="{ row }">

          <!-- v-if="hasRole('disk-monitor:admin')" -->
          <TableActionButton
            action="edit"
            @click="projectFormDialogRef.edit(row)">
            编辑
          </TableActionButton>
          <TableActionButton
            action="detail"
            @click="router.push({path: `/project/${row.id}`})">
            详情
          </TableActionButton>

        </template>
      </ElTableColumn>
    </DataTable>
  </div>
  <ProjectFormDialog
    ref="projectFormDialogRef"
    @submitted="query" />
</template>
