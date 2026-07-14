<script setup>
import { ElButton, ElTableColumn, ElFormItem, ElInput, ElMessageBox, ElMessage } from 'element-plus';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import storageClusterApi from '@/api/storage-cluster-api';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { useQuery, useQueryParams } from '@/composables/query';
import { hasRole } from '@/utils/authorization';
import StorageClusterFormDialog from './components/StorageClusterFormDialog.vue';
import Progress from '@/components/form//Progress.vue';
const router = useRouter();
const formDialogRef = ref();

const { queryParams, reset } = useQueryParams(() => ({
  page: 1,
  size: 20,
  nameLike: null,
}));

const { result, querying, query } = useQuery(() => storageClusterApi.fetch(queryParams.value), {
  content: [],
  total: 0,
});

function confirmDelete(row) {
  ElMessageBox.confirm(`确认删除存储集群「${row.name}」？此操作不可撤销。`, '提示', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    beforeClose: (action, instance, done) => {
      if (action === 'confirm') {
        instance.confirmButtonLoading = true;
        storageClusterApi.deleteById(row.id).then(() => {
          done();
          ElMessage.success('删除成功');
          query();
        }).finally(() => {
          instance.confirmButtonLoading = false;
        });
      } else {
        done();
      }
    },
  }).then(() => {}).catch(() => {});
}

query();
</script>

<template>
  <div class="storage-cluster-list-page">
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
      <ElFormItem label="集群名称">
        <ElInput
          v-model="queryParams.nameLike"
          :clearable="true"
          placeholder="根据集群名称搜索" />
      </ElFormItem>
    </FilterForm>

    <div
      v-if="hasRole('disk-monitor:admin')"
      class="mt-2.5 flex justify-end">
      <ElButton
        type="primary"
        @click="formDialogRef.create()">
        新增集群
      </ElButton>
    </div>

    <DataTable
      :pagination="{
        page: queryParams.page,
        pageSize: queryParams.size,
        total: result.total,
        pageSizes: [20, 50, 100, 200, 500],
        hideOnSinglePage: true,
        showJumper: true,
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
        label="集群名称"
        prop="name"
        align="center"
        sortable="custom"
        min-width="150"
      />
      <ElTableColumn
        label="描述"
        prop="description"
        align="center"
        min-width="200"
        show-overflow-tooltip
      />
      <ElTableColumn
        label="协议"
        prop="protocol"
        align="center"
        min-width="80">
        <template #default="{ row }">
          {{ row.protocol?.toUpperCase() }}
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="TLS 校验"
        prop="tls_verify"
        align="center"
        min-width="90">
        <template #default="{ row }">
          {{ row.protocol === 'https' ? (row.tls_verify ? '开启' : '关闭') : '不适用' }}
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
        min-width="180"
        fixed="right"
      >
        <template #header>
          <ElButton
            size="small"
            plain
            type="primary"
            @click="formDialogRef.edit()">
            添加存储集群
          </ElButton>
        </template>
        <template #default="{ row }">
          <ElButton
            size="small"
            plain
            @click="router.push({ path: `/admin/storage-cluster/${row.id}` })">
            详情
          </ElButton>
          <ElButton
            size="small"
            type="primary"
            link
            @click="formDialogRef.edit(row)">
            编辑
          </ElButton>
          <ElButton
            size="small"
            type="danger"
            link
            @click="confirmDelete(row)">
            删除
          </ElButton>
        </template>
      </ElTableColumn>
    </DataTable>

    <StorageClusterFormDialog
      ref="formDialogRef"
      @submitted="query" />
  </div>
</template>

<style scoped>
:deep(.el-form-item) {
  margin-bottom: 20px;
}
</style>
