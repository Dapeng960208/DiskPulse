<script setup>
import { ElButton, ElDropdown, ElDropdownItem, ElDropdownMenu, ElTableColumn, ElFormItem, ElInput, ElMessageBox, ElMessage } from 'element-plus';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import storageClusterApi from '@/api/storage-cluster-api';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { useQuery, useQueryParams } from '@/composables/query';
import { hasRole } from '@/utils/authorization';
import StorageClusterFormDialog from './components/StorageClusterFormDialog.vue';
import Progress from '@/components/form//Progress.vue';
import { useResponsiveTableColumns } from '@/composables/responsive-table-columns';
import StorageTypeTag from '@/components/data/StorageTypeTag.vue';
const router = useRouter();
const formDialogRef = ref();
const { showCapacityColumns, showSecondaryColumns } = useResponsiveTableColumns();

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
  ElMessageBox.confirm(`确认删除存储集群「${row.name}」？此操作不可撤销。`, '删除存储集群', {
    type: 'warning',
    confirmButtonText: '删除集群',
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
      <ElFormItem
        label="集群名称"
        class="query-form-field--wide">
        <ElInput
          v-model="queryParams.nameLike"
          :clearable="true"
          placeholder="根据集群名称搜索" />
      </ElFormItem>
    </FilterForm>

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
        show-overflow-tooltip
      />
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="存储类型"
        align="center"
        min-width="90">
        <template #default="{ row }">
          <StorageTypeTag :value="row.storage_type" />
        </template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="描述"
        prop="description"
        align="center"
        min-width="220"
        show-overflow-tooltip
      />
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="协议"
        prop="protocol"
        align="center"
        min-width="80">
        <template #default="{ row }">
          {{ row.protocol?.toUpperCase() }}
        </template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="TLS 校验"
        prop="tls_verify"
        align="center"
        min-width="90">
        <template #default="{ row }">
          {{ row.protocol === 'https' ? (row.tls_verify ? '开启' : '关闭') : '不适用' }}
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
          <span v-if="row.limit">{{ row.limit>=1024 ? `${(row.limit/1024).toFixed(1)} T`: `${row.limit}` }}</span>
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
          <span>{{ row.used>=1024 ? `${(row.used/1024).toFixed(1)} T`: `${row.used} G` }}</span>
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
        fixed="right"
      >
        <template #header>
          <ElButton
            v-if="hasRole('disk-monitor:admin')"
            size="small"
            plain
            type="primary"
            @click="formDialogRef.edit()">
            添加集群
          </ElButton>
        </template>
        <template #default="{ row }">
          <div class="list-row-actions">
            <ElButton
              size="small"
              plain
              @click="router.push({ path: `/admin/storage-cluster/${row.id}` })">
              详情
            </ElButton>
            <ElDropdown
              v-if="hasRole('disk-monitor:admin')"
              trigger="click"
              placement="bottom-end">
              <ElButton
                class="list-row-actions__more"
                size="small"
                plain
                aria-label="更多操作">
                ···
              </ElButton>
              <template #dropdown>
                <ElDropdownMenu>
                  <ElDropdownItem @click="formDialogRef.edit(row)">
                    编辑
                  </ElDropdownItem>
                  <ElDropdownItem
                    class="list-row-actions__danger"
                    @click="confirmDelete(row)">
                    删除
                  </ElDropdownItem>
                </ElDropdownMenu>
              </template>
            </ElDropdown>
          </div>
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
