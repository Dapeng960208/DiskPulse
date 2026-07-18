<script setup>
import { ElButton, ElFormItem, ElInput, ElTableColumn, ElTag, ElMessageBox, ElMessage, ElSelect, ElOption } from 'element-plus';
import { ref, onBeforeMount } from 'vue';
import { useRoute } from 'vue-router';
import usersApi from '@/api/users-api';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { useQuery, useQueryParams } from '@/composables/query';
import UserFormDialog from './components/UserFormDialog.vue';
import UserAvatar from '@/components/data/UserAvatar.vue';
// 定义引用
const userFormDialogRef = ref();
const syncing = ref(false);
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
  ElMessageBox.confirm(`确认删除用户「${row.rd_username}」？此操作不可撤销。`, '删除用户', {
    type: 'warning',
    confirmButtonText: '删除用户',
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

async function syncLdapUsers() {
  if (syncing.value) return;
  syncing.value = true;

  const confirmed = await ElMessageBox.confirm(
    '缺失的在职用户会转为离职；离职用户重新出现会恢复在职；公共用户类型不会自动改变；不会删除任何用户。',
    '同步 LDAP 用户',
    {
      type: 'warning',
      confirmButtonText: '开始同步',
      cancelButtonText: '取消',
    },
  ).then(() => true).catch(() => false);

  if (!confirmed) {
    syncing.value = false;
    return;
  }

  try {
    const stats = await usersApi.syncLdap();
    ElMessage.success(
      `LDAP 用户 ${stats.ldap_total}；新增 ${stats.created}；更新 ${stats.updated}；恢复在职 ${stats.reactivated}；标记离职 ${stats.marked_inactive}`,
    );
    queryParams.value.page = 1;
    await query();
  } finally {
    syncing.value = false;
  }
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
      <ElFormItem
        label="用户名"
        class="query-form-field--wide">
        <ElInput
          v-model="queryParams.nameLike"
          :clearable="true"
          placeholder="根据用户名搜索" />
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
        label="用户名"
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
        label="姓名"
        prop="username"
        align="center"
        sortable
        min-width="100"
      />
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
        label="账户类型"
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
        label="告警状态"
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
        label="存储用量"
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
      <ElTableColumn
        align="right"
        width="196"
        fixed="right">
        <template #header>
          <ElButton
            size="small"
            plain
            type="primary"
            @click="userFormDialogRef.edit()">
            新增用户
          </ElButton>
          <ElButton
            size="small"
            plain
            type="success"
            :disabled="syncing"
            :loading="syncing"
            @click="syncLdapUsers">
            同步LDAP
          </ElButton>
        </template>

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
  </div>
</template>
<style scoped>
.user-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  margin: var(--spacing-sm) 0;
}

:deep(.el-form-item){
  margin-bottom: 0px;
}
</style>
