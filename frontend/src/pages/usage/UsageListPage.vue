<script setup>
import { ElButton, ElFormItem, ElInput, ElLink, ElTableColumn, ElTag,ElMessage, ElDescriptions, ElDescriptionsItem,ElMessageBox,ElDatePicker } from 'element-plus';
import { computed, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import storageUsageApi from '@/api/storage-usage-api.js';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { hasRole } from '@/utils/authorization';
import { useQuery, useQueryParams } from '@/composables/query';
import Progress from '@/components/form/Progress.vue'
import GroupSelect from '@/components/form/GroupSelect.vue'
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import GroupTagSelect from '@/components/form/GroupTagSelect.vue';
import StorageClusterSelect from '@/components/form/StorageClusterSelect.vue';
import UsageFormDialog from './components/UsageFormDialog.vue'
import RdUserSelect from '@/components/form/RdUserSelect.vue';
import { useCurrentUser } from '@/stores/current-user';
import { exportReport } from '@/utils/common.js';
import ExportDialog from '@/components/form/ExportDialog.vue';
import { canRenderQuotaProgress, formatQuotaLimit } from '@/utils/quota';
import { formatStorageTargetType } from '@/utils/storage-resource';
const exportRef =ref(null);
const currentUser = useCurrentUser();
const router = useRouter();
const storageUsageFormDialogRef = ref();
const { queryParams, reset } = useQueryParams(() => ({
  page: 1,
  size: 20,
  project_id: null,
  group_tag_id: null,
  group_id: null,
  storage_cluster_id: null,
  user_id: null,
  nameLike:currentUser.extensionAttributes?.rdUsername
}));


const { result, querying, query } = useQuery(() => storageUsageApi.fetch(queryParams.value), {
  content: [],
  totalElements: 0,
});
const handleExport = (exportType) => {
  queryParams.value.export_type = exportType;
  exportReport(storageUsageApi.exportStorageUsages(queryParams.value));
};
const handleProjectChange = (projectId) => {
  queryParams.value.project_id = projectId;
  queryParams.value.group_tag_id = null;
  queryParams.value.group_id = null;
  queryParams.value.storage_cluster_id = null;
};
const handleGroupTagChange = (groupTagId) => {
  queryParams.value.group_tag_id = groupTagId;
  queryParams.value.group_id = null;
  queryParams.value.storage_cluster_id = null;
};
const openExport = () => exportRef.value?.open?.();
function confirmBackUp(row) {
  ElMessageBox.confirm(`确认移动此目录${row.linux_path}至备份目录？此操作不可撤销。`, '提示', {
    type: 'warning',
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    beforeClose: (action, instance, done) => {
      if (action === 'confirm') {
        instance.confirmButtonLoading = true;
        storageUsageApi.backUpStorageUsageById(row.id).then(() => {
          done();
          ElMessage.success('移动目录至备份目录成功');
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
  <div class="usage-list-page">
    <FilterForm
      @query="{
        queryParams.page = 1;
        query();
      }"
      @reset="{
        reset();
        query();
      }"
      @export="openExport"
    >
      <ElFormItem label="项目">
        <ProjectSelect
          :model-value="queryParams.project_id"
          :multiple="false"
          :clearable="true"
          @update:model-value="handleProjectChange" />
      </ElFormItem>
      <ElFormItem label="项目组标签">
        <GroupTagSelect
          :model-value="queryParams.group_tag_id"
          :clearable="true"
          @update:model-value="handleGroupTagChange" />
      </ElFormItem>
      <ElFormItem label="Linux目录">
        <ElInput
          v-model="queryParams.nameLike"
          placeholder="根据关键字模糊搜素" />
      </ElFormItem>
      <ElFormItem label="项目组">
        <GroupSelect
          v-model="queryParams.group_id"
          :project-id="queryParams.project_id"
          :group-tag-id="queryParams.group_tag_id"
          :multiple="false"
          :clearable="true" />
      </ElFormItem>
      <ElFormItem label="存储集群">
        <StorageClusterSelect
          v-model="queryParams.storage_cluster_id"
          :multiple="false"
          :clearable="true" />
      </ElFormItem>
      <ElFormItem label="研发用户名">
        <RdUserSelect
          v-model="queryParams.user_id"
          :multiple="false"
          :clearable="true" />
      </ElFormItem>
      <template #exportExcel></template>
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
      <ElTableColumn type="expand">
        <template #default="props">
          <ElDescriptions
            border
            :column="3"
            class="usage-descriptions">
            <ElDescriptionsItem
              label="使用量"
              align="center">{{ props.row?.used }} G</ElDescriptionsItem>
            <ElDescriptionsItem
              label="硬利用率"
              align="center">{{ props.row?.use_ratio }} %</ElDescriptionsItem>
            <ElDescriptionsItem
              label="软利用率"
              align="center">{{ props.row?.soft_use_ratio ?? '-' }} %</ElDescriptionsItem>
            <ElDescriptionsItem
              label="类型"
              align="center"
              :span="1">{{ props.row?.type }}</ElDescriptionsItem>
            <ElDescriptionsItem
              label="修改时间(Change Time)"
              align="center">{{ props.row?.change_time }}</ElDescriptionsItem>
            <ElDescriptionsItem
              label="访问时间(Access Time)"
              align="center">{{ props.row?.access_time }}</ElDescriptionsItem>
            <ElDescriptionsItem
              label="权限组"
              align="center"
              :span="1">{{ props.row?.gid }}</ElDescriptionsItem>
            <ElDescriptionsItem
              label="Inode编号"
              align="center"
              :span="1">{{ props.row?.inode }}</ElDescriptionsItem>
            <ElDescriptionsItem
              label="硬链接数量"
              align="center"
              :span="1">{{ props.row?.links }}</ElDescriptionsItem>
            <ElDescriptionsItem
              label="系统的I/O块大小"
              align="center"
              :span="1">{{ props.row?.blocks }}</ElDescriptionsItem>
            <ElDescriptionsItem
              label="IO块(IO Block)"
              align="center"
              :span="1">{{ props.row?.io_block }}</ElDescriptionsItem>
            <ElDescriptionsItem
              label="设备的标识号"
              align="center"
              :span="1">{{ props.row?.device }}</ElDescriptionsItem>
          </ElDescriptions>
        </template>
      </ElTableColumn>

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
        label="项目"
        align="center"
        min-width="80">
        <template #default="{ row }">
          <span>{{ row.project?.name || '-' }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="项目组标签"
        align="center"
        min-width="80">
        <template #default="{ row }">
          <span>{{ row.group_tag?.name || '-' }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="项目组"
        align="center"
        min-width="50"
      >
        <template #default="{ row }">
          <ElTag v-if="row.group">
            {{ row.group.name }}
          </ElTag>
          <ElTag v-else>默认</ElTag>
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
        label="存储类型"
        align="center"
        min-width="70">
        <template #default="{ row }">
          <span>{{ row.storage_cluster?.storage_type || '-' }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="存储目标"
        align="center"
        min-width="160">
        <template #default="{ row }">
          <span>{{ formatStorageTargetType(row.storage_target?.type) }} / {{ row.storage_target?.name || '-' }}</span>
        </template>
      </ElTableColumn>

      <ElTableColumn
        label="Linux路径"
        align="center"
        sortable="custom"
        prop="linux_path"
        min-width="200"
      />
      <ElTableColumn
        label="文件数量"
        align="center"
        sortable="custom"
        prop="file_used"
        min-width="60"
      />
      <ElTableColumn
        label="权限"
        align="center"
        sortable="custom"
        prop="access"
        min-width="60"
      />
      <ElTableColumn
        label="修改时间"
        align="center"
        sortable="custom"
        prop="modify_time"
        min-width="80"
      />
      <ElTableColumn
        label="硬限额"
        sortable="custom"
        align="center"
        prop="limit"
        min-width="50"
      >
        <template #default="{ row }">
          <span v-if="row.limit">{{ formatQuotaLimit(row.limit) }}</span>
          <ElTag
            v-else
            type="danger">无限额</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="软限额"
        sortable="custom"
        align="center"
        prop="soft_limit"
        min-width="60"
      >
        <template #default="{ row }">
          <span v-if="row.soft_limit">{{ formatQuotaLimit(row.soft_limit, { emptyText: '无软限额' }) }}</span>
          <ElTag
            v-else
            type="info">无软限额</ElTag>
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
        label="硬利用率(%)"
        align="center"
        prop="use_ratio"
        sortable="custom"
        width="200"
      >
        <template #default="{ row }">
          <Progress
            v-if="canRenderQuotaProgress({ used: row.used, total: row.limit })"
            :used="row.used"
            :total="row.limit"
            :show-numbers="false" />
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="软利用率(%)"
        align="center"
        prop="soft_use_ratio"
        sortable="custom"
        width="200"
      >
        <template #default="{ row }">
          <Progress
            v-if="canRenderQuotaProgress({ used: row.used, total: row.soft_limit })"
            :used="row.used"
            :total="row.soft_limit"
            :show-numbers="false" />
          <ElTag
            v-else
            type="info">无软限额</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        align="center"
        min-width="50">
        <template
          v-if="hasRole('disk-monitor:admin')"
          #header>
          <ElButton
            v-if="hasRole('disk-monitor:admin')"
            size="small"
            plain
            type="primary"
            @click="storageUsageFormDialogRef.edit()">
            新增
          </ElButton>
        </template>
        <template #default="{ row }">
          <ElButton
            size="small"
            plain
            @click="router.push({path: `/usage/${row.id}`})">
            详情
          </ElButton>
          <!-- <ElButton size="small" plain @click="storageUsageFormDialogRef.edit(row)" v-if="hasRole('disk-monitor:admin')">
          编辑
          </ElButton> -->
          <ElButton
            v-if="hasRole('disk-monitor:admin') && false"
            size="small"
            type="danger"
            plain
            @click="confirmBackUp(row)">
            移至备份
          </ElButton>
        </template>
      </ElTableColumn>
    </DataTable>
    <UsageFormDialog
      ref="storageUsageFormDialogRef"
      @submitted="query" />
    <ExportDialog
      ref="exportRef"
      :export-type="queryParams.export_type"
      @submitted="handleExport"></ExportDialog>
  </div>
</template>

<style lang="scss" scoped>
@import '@/styles/mixins.scss';

.usage-list-page {
  @include page-container;
}
</style>
