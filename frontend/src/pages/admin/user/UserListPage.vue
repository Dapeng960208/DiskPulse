<script setup>
import { ElButton, ElFormItem, ElInput, ElTableColumn, ElDivider, ElTag,ElCard,ElMessageBox,ElMessage,ElSelect,ElOption } from 'element-plus';
import { ref, onBeforeMount } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import usersApi from '@/api/users-api';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { useQuery, useQueryParams } from '@/composables/query';
import UserFormDialog from './components/UserFormDialog.vue';
import { hasRole } from '@/utils/authorization';
import UserAvatar from '@/components/data/UserAvatar.vue';
// 定义引用
const userFormDialogRef = ref();
const router = useRouter();
const route = useRoute();
// 初始化查询参数
const { queryParams, reset } = useQueryParams(() => ({
  page: 1,
  size: 20,
  nameLike: null,
}));

// 使用查询钩子
const { result, querying, query } = useQuery(() => usersApi.fetch(queryParams.value), {
  content: [],
  totalElements: 0,
});

function confirmDelete(row) {
  ElMessageBox.confirm(`确认删除 ${row.rd_username}？此操作不可撤销。`, '提示', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    beforeClose: (action, instance, done) => {
      if (action === 'confirm') {
        instance.confirmButtonLoading = true;
        usersApi.deleteById(row.id).then(() => {
          done();
          ElMessage.success('删除成功');
          query();
        }).finally(() => instance.confirmButtonLoading = false);
      } else {
        done();
      }
    },
  }).then(() => {}).catch(() => {});
}

// 初始查询
onBeforeMount(() => {
  if (route.query?.nameLike) {
    queryParams.value.nameLike = route.query.nameLike;
  }
  query();
});
</script>

<template>
  <div class="user-list-page">
    <!-- 过滤表单 -->
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
      <ElFormItem label="研发用户名">
        <ElInput
          v-model="queryParams.nameLike"
          :clearable="true"
          placeholder="根据研发用户名搜索" />
      </ElFormItem>
      <ElFormItem label="账户类型">
        <ElSelect
          v-model="queryParams.user_type"
          placeholder="请选择账户类型">
          <ElOption
            label="离职账户"
            :value="0" />
          <ElOption
            label="公共账户"
            :value="1" />
          <ElOption
            label="在职账户"
            :value="2" />
        </ElSelect>
      </ElFormItem>
    </FilterForm>

    <!-- 数据表格 -->
    <DataTable
      :pagination="{
        page: queryParams.page,
        pageSize: queryParams.size,
        total: result.total,
        pageSizes: [20, 50, 100, 200, 500],
        hideOnSinglePage: true,
        showJumper: true
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
        label="研发用户名"
        align="center"
        sortable="custom"
      >
        <template #default="{ row }">
          <div style="display: flex; align-items: center; justify-content: center;">
            <UserAvatar
              v-if="row.avatar_url"
              :src="row.avatar_url" />
            <span style="margin-left: 8px;">{{ row.rd_username }} </span>
          </div>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="域账号"
        prop="username"
        align="center"
        sortable
        min-width="100"
      />
      <ElTableColumn
        label="账号类型"
        align="center"
        min-width="100"
      >
        <template #default="{ row }">
          <ElTag v-if="row.user_type===2">在职账户</ElTag>
          <ElTag
            v-if="row.user_type===1"
            type="warning">公共账户</ElTag>
          <ElTag
            v-if="row.user_type===0"
            type="danger">离职账户</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="是否告警"
        align="center"
        min-width="100"
      >
        <template #default="{ row }">
          <ElTag v-if="row.is_alert">是</ElTag>
          <ElTag
            v-else
            type="danger">否</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="累计使用存储"
        align="center"
        sortable
        prop="storage_used"
        min-width="100"
      >
        <template #default="{ row }">
          <span v-if="row.storage_used>1024">{{ parseFloat(row.storage_used/1024).toFixed(2) }} TB </span>
          <span v-else>{{ row.storage_used }} GB </span>
        </template>
      </ElTableColumn>
      <!-- <ElTableColumn
        label="研发用户名"
        prop="rd_username"
        align="center"
        sortable="custom"
        min-width="100"
      >
      <template #default="{ row }">
        <span>{{ row.rd_username }}</span>
        <ElTag v-if="row.user_type===1" type="warning" class="ml-2.5">公共账户</ElTag>
        <ElTag v-if="row.user_type===0" type="danger" class="ml-2.5">离职账户</ElTag>
      </template>
      </ElTableColumn> -->
      <ElTableColumn
        label="邮箱"
        prop="email"
        align="center"
        sortable
        min-width="100"
      />
      <ElTableColumn
        label="部门"
        prop="department"
        align="center"
        sortable
        min-width="100"
      />
      <ElTableColumn
        align="center"
        min-width="120"
        fixed="right">
        <template #default="{ row }">
          <ElButton
            size="small"
            type="primary"
            link
            @click="userFormDialogRef.edit(row)">
            编辑
          </ElButton>
          <ElButton
            type="danger"
            size="small"
            link
            @click="confirmDelete(row)"
          >
            删除
          </ElButton>
        </template>
      </ElTableColumn>
    </DataTable>


    <!-- 用户表单对话框 -->
    <UserFormDialog
      ref="userFormDialogRef"
      @submitted="query" />
  </div></template>
<style scoped>
:deep(.el-form-item){
  margin-bottom: 0px;
}
</style>
