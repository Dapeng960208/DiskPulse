<script setup>
import { ElButton, ElFormItem, ElInput, ElMessageBox,ElMessage, ElTableColumn, ElTag,ElLink} from 'element-plus';
import { computed, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import storageBackUpRecordApi from '@/api/storage-back-up-record-api.js';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { hasRole } from '@/utils/authorization';
import { useQuery, useQueryParams } from '@/composables/query';
import RdUserSelect from '@/components/form/RdUserSelect.vue';
import { useCurrentUser } from '@/stores/current-user';
import TableActionButton from '@/components/basic/TableActionButton.vue';
const exportRef =ref(null);
const currentUser = useCurrentUser();
const router = useRouter();
const { queryParams, reset } = useQueryParams(() => ({
  page: 1,
  size: 20,
}));


const { result, querying, query } = useQuery(() => storageBackUpRecordApi.fetch(queryParams.value), {
  content: [],
  totalElements: 0,
});
function confirmDeleteBackUp(row) {
  ElMessageBox.confirm(`确认删除数据备份「${row.destination_path}」？此操作不可撤销。`, '删除数据备份', {
    type: 'warning',
    confirmButtonText: '删除备份',
    cancelButtonText: '取消',
    beforeClose: (action, instance, done) => {
      if (action === 'confirm') {
        instance.confirmButtonLoading = true;
        storageBackUpRecordApi.deleteById(row.id).then(() => {
          done();
          ElMessage.success('备份删除成功');
          query();
        }).finally(() => instance.confirmButtonLoading = false);
      } else {
        done();
      }
    },
  }).then(() => {}).catch(() => {});
}

function confirmRollBack(row) {
  ElMessageBox.confirm(`确认将数据备份「${row.destination_path}」回滚至「${row.source_path}」？此操作不可撤销。`, '回滚数据备份', {
    type: 'warning',
    confirmButtonText: '开始回滚',
    cancelButtonText: '取消',
    beforeClose: (action, instance, done) => {
      if (action === 'confirm') {
        instance.confirmButtonLoading = true;
        storageBackUpRecordApi.rollBackedBackUpStorageById(row.id).then(() => {
          done();
          ElMessage.success('备份回滚成功');
          query();
        }).finally(() => instance.confirmButtonLoading = false);
      } else {
        done();
      }
    },
  }).then(() => {}).catch(() => {});
}

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
      @export="exportRef.open()"
    >
      <ElFormItem
        label="Linux目录"
        class="query-form-field--wide">
        <ElInput
          v-model="queryParams.nameLike"
          placeholder="根据关键字模糊搜素" />
      </ElFormItem>
      <ElFormItem label="研发用户名">
        <RdUserSelect
          v-model="queryParams.user_id"
          :multiple="false"
          :clearable="true" />
      </ElFormItem>
    </FilterForm>
    <DataTable
      class="h-full"
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
        label="备份ID"
        align="center"
        sortable="custom"
        prop="id"
        min-width="50"
      />
      <ElTableColumn
        label="研发用户名"
        align="center"
        min-width="80"
      >
        <template #default="{ row }">
          <span>{{ row.user?.rd_username }}</span>
          <ElTag
            v-if="row.user.user_type===1"
            type="warning"
            class="ml-2.5">公共账户</ElTag>
          <ElTag
            v-if="row.user.user_type===0"
            type="danger"
            class="ml-2.5">离职账户</ElTag>
        </template>
      </ElTableColumn>

      <ElTableColumn
        label="源路径"
        align="center"
        sortable="custom"
        prop="source_path"
        min-width="120"
      />
      <ElTableColumn
        label="备份路径"
        align="center"
        sortable="custom"
        prop="destination_path"
        min-width="120"
      />
      <ElTableColumn
        label="备份开始时间"
        align="center"
        sortable="custom"
        prop="start_time"
        min-width="60"
      />
      <ElTableColumn
        label="备份结束时间"
        align="center"
        sortable="custom"
        prop="end_time"
        min-width="60"
      />
      <ElTableColumn
        label="状态"
        align="center"
        sortable="custom"
        prop="modify_time"
        min-width="80"
      >
        <template #default="{ row }">
          <ElTag
            v-if="row.status===0"
            type="danger"
            class="ml-2.5">备份失败</ElTag>
          <ElTag
            v-if="row.status===1"
            class="ml-2.5">备份中</ElTag>
          <ElTag
            v-if="row.status===2"
            type="success"
            class="ml-2.5">备份成功</ElTag>
          <ElTag
            v-if="row.status===3"
            type="danger"
            class="ml-2.5">删除备份失败</ElTag>
          <ElTag
            v-if="row.status===4"
            class="ml-2.5">删除备份中</ElTag>
          <ElTag
            v-if="row.status===5"
            type="success"
            class="ml-2.5">删除备份成功</ElTag>
          <ElTag
            v-if="row.status===6"
            type="danger"
            class="ml-2.5">回滚备份失败</ElTag>
          <ElTag
            v-if="row.status===7"
            class="ml-2.5">回滚备份中</ElTag>
          <ElTag
            v-if="row.status===8"
            type="success"
            class="ml-2.5">回滚备份成功</ElTag>
          <ElTag
            v-if="row.status===9"
            type="success"
            class="ml-2.5">业务代表审批中</ElTag>
          <ElTag
            v-if="row.status===10"
            type="danger"
            class="ml-2.5">取消自动备份</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="BPM电子流"
        align="center"
        min-width="80"
      >
      <!-- <template #default="{ row }">
        <ElLink :href="`https://bpm.engiant.com/workbench/process-instances/${row.process_uid}`" style="color: #409eff" v-if="row.process_uid">{{ row.process_uid }}</ElLink>
      </template> -->
      </ElTableColumn>
      <ElTableColumn
        align="right"
        width="160"
        fixed="right">
        <template #default="{ row }">
          <TableActionButton
            v-if="hasRole('disk-monitor:admin') && row.status===2"
            action="delete"
            @click="confirmDeleteBackUp(row)">
            删除备份
          </TableActionButton>
          <TableActionButton
            v-if="hasRole('disk-monitor:admin') && row.status===2"
            action="rollback"
            @click="confirmRollBack(row)">
            回滚备份
          </TableActionButton>
        </template>
      </ElTableColumn>
    </DataTable>
  </div>
</template>
