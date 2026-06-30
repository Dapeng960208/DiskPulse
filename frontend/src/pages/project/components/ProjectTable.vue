<script setup>
import { ElButton, ElFormItem, ElInput, ElTag, ElTableColumn,ElTabPane,ElTabs } from 'element-plus';
import { computed, ref } from 'vue';
import {  useRouter } from 'vue-router';
import projectApi from '@/api/project-api';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { useQuery, useQueryParams } from '@/composables/query';
import { hasRole } from '@/utils/authorization';
import Progress from '@/components/form//Progress.vue';
import ProjectFormDialog from './ProjectFormDialog.vue';
import UserAvatar from '@/components/data/UserAvatar.vue'
const projectFormDialogRef = ref();
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
      <ElFormItem label="项目名">
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
        min-width="80"
      />
      <ElTableColumn
        label="PT经理"
        align="center"
        sortable
        min-width="100"
      >
        <template #default="{ row }">
          <div style="display: flex; align-items: center; justify-content: center;">
            <UserAvatar
              v-if="row.pt_user && row.pt_user.avatar_url"
              :src="row.pt_user.avatar_url" />
            <span style="margin-left: 8px;">{{ row?.pt_user?.rd_username }} {{ row?.pt_user?.username }}</span>
          </div>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="开发代表"
        align="center"
        sortable
        min-width="100"
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
        label="限额"
        sortable="custom"
        align="center"
        prop="limit"
        min-width="50"
      >
        <template #default="{ row }">
          <span v-if="row.limit">{{ row.limit>=1024 ? `${(row.limit/1024).toFixed(1)} T`: `${row.limit}` }}</span>
          <ElTag
            v-else
            type="danger">无限额</ElTag>
        </template>
      </ElTableColumn>
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
        align="right"
        min-width="120">
        <template #header>
          <ElButton
            size="small"
            plain
            type="primary"
            @click="projectFormDialogRef.edit()">
            添加项目
          </ElButton>
        </template>
        <template #default="{ row }">

          <!-- v-if="hasRole('disk-monitor:admin')" -->
          <ElButton
            size="small"
            plain
            @click="projectFormDialogRef.edit(row)">
            编辑
          </ElButton>
          <ElButton
            size="small"
            plain
            @click="router.push({path: `/project/${row.id}`})">
            详情
          </ElButton>

        </template>
      </ElTableColumn>
    </DataTable>
  </div>
  <ProjectFormDialog
    ref="projectFormDialogRef"
    @submitted="query" />
</template>
