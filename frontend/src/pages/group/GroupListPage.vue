<script setup>
import { ElButton, ElDropdown, ElDropdownItem, ElDropdownMenu, ElFormItem, ElInput, ElLink, ElTableColumn, ElTag, ElCard, ElSelect, ElDescriptions, ElDescriptionsItem,ElMessageBox,ElMessage,ElDatePicker, ElSwitch } from 'element-plus';
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
import VolumeSelect from '@/components/form/VolumeSelect.vue';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import GroupTagSelect from '@/components/form/GroupTagSelect.vue';
import StorageClusterSelect from '@/components/form/StorageClusterSelect.vue';
import GroupFormDialog from './components/GroupFormDialog.vue';
import { canRenderQuotaProgress, formatQuotaLimit } from '@/utils/quota';
import { formatStorageTargetType } from '@/utils/storage-resource';
import QuotaAdjustmentDialog from '@/components/form/QuotaAdjustmentDialog.vue';
import { useResponsiveTableColumns } from '@/composables/responsive-table-columns';
import StorageTypeTag from '@/components/data/StorageTypeTag.vue';

const groupFormDialogRef = ref();
const quotaAdjustmentDialogRef = ref();
const { showCapacityColumns, showSecondaryColumns } = useResponsiveTableColumns();
const { queryParams, reset } = useQueryParams(() => ({
  page: 1,
  size: 20,
}));


const router = useRouter();
const { result, querying, query } = useQuery(() => groupApi.fetch(queryParams.value), {
  content: [],
  totalElements: 0,
});
const selectedGroupTagLabel = ref(null);
const selectedVolumeLabel = ref(null);
const selectedQtreeLabel = ref(null);
const activeAdvancedCount = computed(() => [
  queryParams.value.group_tag_id,
  queryParams.value.volume_id,
  queryParams.value.qtree_id,
].filter(Boolean).length);

function changeProjectFilter(projectId) {
  queryParams.value.project_id = projectId;
}

function changeClusterFilter(clusterId) {
  queryParams.value.storage_cluster_id = clusterId;
  queryParams.value.volume_id = null;
  queryParams.value.qtree_id = null;
  selectedVolumeLabel.value = null;
  selectedQtreeLabel.value = null;
}

function changeVolumeFilter(volumeId) {
  queryParams.value.volume_id = volumeId;
  queryParams.value.qtree_id = null;
  selectedQtreeLabel.value = null;
}

function changeQtreeFilter(qtreeId) {
  queryParams.value.qtree_id = qtreeId;
  queryParams.value.volume_id = null;
  selectedVolumeLabel.value = null;
}

function resetFilters() {
  reset();
  selectedGroupTagLabel.value = null;
  selectedVolumeLabel.value = null;
  selectedQtreeLabel.value = null;
  query();
}

function refreshAfterFilterRemoval() {
  queryParams.value.page = 1;
  query();
}

function removeGroupTagFilter() {
  queryParams.value.group_tag_id = null;
  selectedGroupTagLabel.value = null;
  refreshAfterFilterRemoval();
}

function removeVolumeFilter() {
  queryParams.value.volume_id = null;
  selectedVolumeLabel.value = null;
  refreshAfterFilterRemoval();
}

function removeQtreeFilter() {
  queryParams.value.qtree_id = null;
  selectedQtreeLabel.value = null;
  refreshAfterFilterRemoval();
}

query();
function confirmDelete(row) {
  ElMessageBox.confirm(`确认删除项目组「${row.name}」？此操作不可撤销。`, '删除项目组', {
    type: 'warning',
    confirmButtonText: '删除项目组',
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
      :advanced-count="activeAdvancedCount"
      @query="{
        queryParams.page = 1;
        query();
      }"
      @reset="resetFilters">
      <ElFormItem
        label="项目组名"
        class="form-item-center query-form-field--wide">
        <ElInput
          v-model="queryParams.nameLike"
          placeholder="根据项目组名模糊搜索" />
      </ElFormItem>
      <ElFormItem
        label="关联项目"
        class="form-item-center">
        <ProjectSelect
          :model-value="queryParams.project_id"
          :multiple="false"
          :clearable="true"
          @update:model-value="changeProjectFilter" />
      </ElFormItem>
      <ElFormItem
        label="存储集群"
        class="form-item-center">
        <StorageClusterSelect
          :model-value="queryParams.storage_cluster_id"
          :clearable="true"
          @update:model-value="changeClusterFilter" />
      </ElFormItem>

      <template #advanced>
        <ElFormItem
          label="项目组标签"
          class="form-item-center">
          <GroupTagSelect
            v-model="queryParams.group_tag_id"
            :clearable="true"
            @selected-label-change="selectedGroupTagLabel = $event" />
        </ElFormItem>
        <ElFormItem
          label="关联存储空间"
          class="form-item-center">
          <VolumeSelect
            :model-value="queryParams.volume_id"
            :storage-cluster-id="queryParams.storage_cluster_id"
            :multiple="false"
            :clearable="true"
            @update:model-value="changeVolumeFilter"
            @selected-label-change="selectedVolumeLabel = $event" />
        </ElFormItem>
        <ElFormItem
          label="关联Qtree（NetApp）"
          class="form-item-center">
          <QtreeSelect
            :model-value="queryParams.qtree_id"
            :storage-cluster-id="queryParams.storage_cluster_id"
            :multiple="false"
            :clearable="true"
            @update:model-value="changeQtreeFilter"
            @selected-label-change="selectedQtreeLabel = $event" />
        </ElFormItem>
      </template>

      <template #active-filters>
        <ElTag
          v-if="queryParams.group_tag_id"
          closable
          @close="removeGroupTagFilter">项目组标签：{{ selectedGroupTagLabel }}</ElTag>
        <ElTag
          v-if="queryParams.volume_id"
          closable
          @close="removeVolumeFilter">关联存储空间：{{ selectedVolumeLabel }}</ElTag>
        <ElTag
          v-if="queryParams.qtree_id"
          closable
          @close="removeQtreeFilter">关联 Qtree：{{ selectedQtreeLabel }}</ElTag>
      </template>
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
            <ElDescriptionsItem label="存储目标">
              <ElTag>
                {{ formatStorageTargetType(props.row.storage_target?.type) }} / {{ props.row.storage_target?.name || '-' }}
              </ElTag>
            </ElDescriptionsItem>
            <ElDescriptionsItem label="Linux路径">
              {{ props.row?.linux_path }}
            </ElDescriptionsItem>

          </ElDescriptions>
        </template>
      </ElTableColumn>

      <ElTableColumn
        v-if="showCapacityColumns"
        label="存储集群"
        align="center"
        prop="storageCluster.name"
        min-width="140"
      >
        <template #default="{ row }">
          <span>{{ row.storage_cluster?.name || '-' }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showCapacityColumns"
        label="存储类型"
        align="center"
        min-width="90">
        <template #default="{ row }">
          <StorageTypeTag :value="row.storage_cluster?.storage_type" />
        </template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="项目组标签"
        align="center"
        min-width="120">
        <template #default="{ row }">
          {{ row.group_tag?.name || '-' }}
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="项目组名"
        align="center"
        prop="name"
        min-width="160"
        show-overflow-tooltip
      />

      <ElTableColumn
        v-if="showCapacityColumns"
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
        v-if="showCapacityColumns"
        label="项目组业务代表"
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
        label="硬限额"
        sortable="custom"
        align="center"
        prop="limit"
        min-width="100"
      >
        <template #default="{ row }">
          <span v-if="row.limit">{{ formatQuotaLimit(row.limit) }}</span>
          <ElTag
            v-else
            type="danger">无硬限额</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showCapacityColumns"
        label="软限额"
        sortable="custom"
        align="center"
        prop="soft_limit"
        min-width="100"
      >
        <template #default="{ row }">
          <span v-if="row.soft_limit">{{ formatQuotaLimit(row.soft_limit, { emptyText: '无软限额' }) }}</span>
          <ElTag
            v-else
            type="warning">无软限额</ElTag>
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
        label="硬限额使用率(%)"
        align="center"
        prop="use_ratio"
        sortable="custom"
        width="240"
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
        label="软限额使用率(%)"
        align="center"
        prop="soft_use_ratio"
        sortable="custom"
        width="240"
      >
        <template #default="{ row }">
          <Progress
            v-if="canRenderQuotaProgress({ used: row.used, total: row.soft_limit })"
            :used="row.used"
            :total="row.soft_limit"
            :show-numbers="false" />
          <ElTag
            v-else
            type="warning">无软限额</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        v-if="false"
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
        width="132">
        <template #header>
          <ElButton
            v-if="hasRole('disk-monitor:admin')"
            size="small"
            plain
            type="primary"
            @click="groupFormDialogRef.edit()">
            添加项目组
          </ElButton>
        </template>
        <template #default="{ row }">
          <div class="list-row-actions">
            <ElButton
              size="small"
              plain
              @click="router.push({path: `/group/${row.id}`})">
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
                  <ElDropdownItem
                    :disabled="row.associate_multiple_groups"
                    :title="row.associate_multiple_groups ? '共享存储目标不能单独调整项目组配额' : ''"
                    @click="quotaAdjustmentDialogRef.open(row)">
                    调整配额
                  </ElDropdownItem>
                  <ElDropdownItem @click="groupFormDialogRef.edit(row)">
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
    <GroupFormDialog
      ref="groupFormDialogRef"
      @submitted="query" />
    <QuotaAdjustmentDialog
      ref="quotaAdjustmentDialogRef"
      resource-type="group"
      @submitted="query" />
  </div>
</template>

<style lang="scss" scoped>
@import '@/styles/mixins.scss';

.group-list-page {
  @include page-container;
}

</style>
