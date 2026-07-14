<script setup>
import { ref } from 'vue';
import { ElButton, ElFormItem, ElInput, ElMessage, ElMessageBox, ElTableColumn } from 'element-plus';
import groupTagApi from '@/api/group-tag-api';
import DataTable from '@/components/data/DataTable.vue';
import QueryForm from '@/components/form/QueryForm.vue';
import { useQuery, useQueryParams } from '@/composables/query';
import GroupTagFormDialog from './components/GroupTagFormDialog.vue';

const dialogRef = ref();
const { queryParams, reset } = useQueryParams(() => ({ page: 1, size: 20, nameLike: null }));
const { result, querying, query } = useQuery(() => groupTagApi.fetch(queryParams.value), {
  content: [],
  total: 0,
});

function confirmDelete(row) {
  ElMessageBox.confirm(`确认删除项目组标签「${row.name}」？`, '提示', { type: 'warning' })
    .then(() => groupTagApi.deleteById(row.id))
    .then(() => {
      ElMessage.success('删除成功');
      query();
    })
    .catch((error) => {
      if (error !== 'cancel' && error !== 'close') {
        ElMessage.error(error?.response?.status === 409
          ? '该标签仍被项目组使用，不能删除'
          : '删除失败，请稍后重试');
      }
    });
}

query();
</script>

<template>
  <div class="group-tag-list-page">
    <QueryForm
      @query="queryParams.page = 1; query()"
      @reset="reset(); query()">
      <ElFormItem label="标签名称">
        <ElInput
          v-model="queryParams.nameLike"
          clearable
          placeholder="根据标签名称搜索" />
      </ElFormItem>
    </QueryForm>
    <DataTable
      :data="result.content"
      :loading="querying"
      :pagination="{ page: queryParams.page, pageSize: queryParams.size, total: result.total }"
      @update:pagination="({ page, pageSize }) => { queryParams.page = page; queryParams.size = pageSize; query(); }">
      <ElTableColumn
        label="标签名称"
        prop="name" />
      <ElTableColumn
        align="right"
        width="160">
        <template #header>
          <ElButton
            size="small"
            plain
            type="primary"
            @click="dialogRef.edit()">新增标签</ElButton>
        </template>
        <template #default="{ row }">
          <ElButton
            link
            type="primary"
            @click="dialogRef.edit(row)">编辑</ElButton>
          <ElButton
            link
            type="danger"
            @click="confirmDelete(row)">删除</ElButton>
        </template>
      </ElTableColumn>
    </DataTable>
    <GroupTagFormDialog
      ref="dialogRef"
      @submitted="query" />
  </div>
</template>
