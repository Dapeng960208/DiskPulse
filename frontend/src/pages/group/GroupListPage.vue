<script setup>
import { ElButton, ElFormItem, ElInput, ElLink, ElTableColumn, ElTag, ElCard, ElSelect, ElDescriptions, ElDescriptionsItem,ElMessageBox,ElMessage,ElDatePicker, ElSwitch } from 'element-plus';
import { computed, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import groupApi from '@/api/group-api.js';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { hasRole } from '@/utils/authorization';
import { useQuery, useQueryParams } from '@/composables/query';
import Progress from '@/components/form/Progress.vue';
import UserAvatar from '@/components/data/UserAvatar.vue'
import QtreeSelect from '@/components/form/QtreeSelect.vue';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import GroupFormDialog from './components/GroupFormDialog.vue';

const groupFormDialogRef = ref();
const { queryParams, reset } = useQueryParams(() => ({
  page: 1,
  size: 20,
}));


const router = useRouter();
const { result, querying, query } = useQuery(() => groupApi.fetch(queryParams.value), {
  content: [],
  totalElements: 0,
});

query();
function confirmDelete(row) {
  ElMessageBox.confirm(`确认删除 ${row.name}？此操作不可撤销。`, '提示', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    beforeClose: (action, instance, done) => {
      if (action === 'confirm') {
        instance.confirmButtonLoading = true;
        groupApi.deleteById(row.id).then(() => {
          done();
          ElMessage.success('删除成功');
          query();
        }).finally(() => instance.confirmButtonLoading = false);
      } else {
        done();
      }
    },
  }).then((
  ) => {

  }).catch(() => {});
}
</script>

<template>
  <div class="group-list-page">
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
        label="关联项目"
        class="form-item-center">
        <ProjectSelect
          v-model="queryParams.project_id"
          :multiple="false"
          :clearable="true" />
      </ElFormItem>
      <ElFormItem
        label="关联Qtree"
        class="form-item-center">
        <QtreeSelect
          v-model="queryParams.qtree_id"
          :multiple="false"
          :clearable="true" />
      </ElFormItem>
      <ElFormItem
        label="项目组名"
        class="form-item-center">
        <ElInput
          v-model="queryParams.nameLike"
          placeholder="根据项目组名模糊搜索" />
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
      <ElTableColumn type="expand">
        <template #default="props">
          <ElDescriptions
            border
            :column="2">
            <ElDescriptionsItem label="挂载">
              <ElTag>
                {{ props.row.qtree?.volume.name }}/{{ props.row.qtree?.name }}
              </ElTag>
            </ElDescriptionsItem>
            <ElDescriptionsItem label="Linux路径">
              {{ props.row?.linux_path }}
            </ElDescriptionsItem>

          </ElDescriptions>
        </template>
      </ElTableColumn>

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
        label="项目组名"
        align="center"
        prop="name"
        min-width="100"
      />

      <ElTableColumn
        label="项目"
        align="center"
        sortable
        min-width="60"
      >
        <template #default="{ row }">
          <ElTag v-if="row.project">
            {{ row.project.name }}
          </ElTag>
          <ElTag v-else>默认</ElTag>
        </template>
      </ElTableColumn>

      <ElTableColumn
        label="项目组业务代表"
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

      <!-- <ElTableColumn
      label="头像"
      align="center"
      min-width="60"
    >
    <template #default="{ row }">
        <UserAvatar v-if="row.in_charge_user && row.in_charge_user.avatar_url" :src="row.in_charge_user.avatar_url" >  </UserAvatar>
      </template>
  </ElTableColumn> -->
      <!-- <ElTableColumn
        label="挂载信息"
        align="center"
        min-width="100"
      >
        <template #default="{ row }">
          <ElTag>
            {{ row.qtree?.volume.name }}/{{ row.qtree?.name }}
          </ElTag>

        </template>
      </ElTableColumn> -->


      <!-- <ElTableColumn
        label="Linux路径"
        align="center"
        prop="linux_path"
        min-width="120"
      /> -->
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
        width="300"
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
        label="开启离职备份"
        align="center"
        prop="back_up_enabled"
        min-width="50"
      >
        <template #default="{ row }">
          <ElSwitch
            v-model="row.back_up_enabled"
            disabled></ElSwitch>
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
            @click="groupFormDialogRef.edit()">
            添加项目组
          </ElButton>
        </template>
        <template #default="{ row }">
          <ElButton
            size="small"
            plain
            @click="router.push({path: `/group/${row.id}`})">
            详情
          </ElButton>
          <ElButton
            size="small"
            plain
            @click="groupFormDialogRef.edit(row)">
            编辑
          </ElButton>
          <ElButton
            type="danger"
            size="small"
            plain
            @click="confirmDelete(row)"
          >
            删除
          </ElButton>
        </template>
      </ElTableColumn>
    </DataTable>
    <GroupFormDialog
      ref="groupFormDialogRef"
      @submitted="query" />
  </div>
</template>

<style lang="scss" scoped>
@import '@/styles/mixins.scss';

.group-list-page {
  @include page-container;
}
</style>
