<script setup>
import { ElFormItem, ElInput, ElMessage, ElTableColumn, ElTag } from 'element-plus';
import { computed, reactive, ref, watch } from 'vue';
import aggregateApi from '@/api/aggregate-api.js';
import qtreeApi from '@/api/qtree-api.js';
import volumeApi from '@/api/volume-api.js';
import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';
import DataTable from '@/components/data/DataTable.vue';
import Progress from '@/components/form/Progress.vue';
import QueryForm from '@/components/form/QueryForm.vue';
import VolumeSelect from '@/components/form/VolumeSelect.vue';
import { canRenderQuotaProgress } from '@/utils/quota';
import { formatCapacity } from '@/utils/capacity';
import { getStorageResourceNativeType } from '@/utils/storage-resource';
import { useResponsiveTableColumns } from '@/composables/responsive-table-columns';

const props = defineProps({
  clusterId: {
    type: Number,
    required: true,
  },
  resourceType: {
    type: String,
    required: true,
    validator: (value) => ['aggregate', 'volume', 'qtree'].includes(value),
  },
});

const resourceDefinitions = {
  aggregate: {
    api: aggregateApi,
    label: '容量池',
    nameLabel: '容量池名',
    detailRoute: 'AggregateDetail',
  },
  volume: {
    api: volumeApi,
    label: '存储空间',
    nameLabel: '存储空间名',
    detailRoute: 'VolumeDetail',
  },
  qtree: {
    api: qtreeApi,
    label: 'Qtree（NetApp）',
    nameLabel: 'Qtree（NetApp）名',
    detailRoute: 'QtreeDetail',
  },
};

const resource = computed(() => resourceDefinitions[props.resourceType]);
const { showCapacityColumns, showSecondaryColumns } = useResponsiveTableColumns();
const result = ref({ content: [], total: 0 });
const querying = ref(false);
const error = ref('');
const queryParams = ref({ page: 1, size: 20, prop: undefined, order: undefined });
const filters = reactive({ nameLike: '', volumeId: null });
const pagination = computed(() => ({
  page: queryParams.value.page,
  pageSize: queryParams.value.size,
  total: result.value.total,
  pageSizes: [20, 50, 100, 200, 500],
  hideOnSinglePage: true,
  showJumper: true,
}));

function buildRequestParams() {
  const { page, size, prop, order } = queryParams.value;
  return {
    page,
    size,
    ...(prop ? { prop } : {}),
    ...(order ? { order } : {}),
    ...(filters.nameLike.trim() ? { nameLike: filters.nameLike.trim() } : {}),
    ...(props.resourceType === 'qtree' && filters.volumeId ? { volume_id: filters.volumeId } : {}),
    storage_cluster_id: props.clusterId,
  };
}

async function query() {
  if (!props.clusterId || !resource.value) return;
  querying.value = true;
  error.value = '';
  try {
    const response = await resource.value.api.fetch(buildRequestParams());
    result.value = {
      content: response?.content || [],
      total: Number(response?.total ?? response?.totalElements) || 0,
    };
  } catch {
    result.value = { content: [], total: 0 };
    error.value = `加载${resource.value.label}失败，请稍后重试`;
    ElMessage.error(error.value);
  } finally {
    querying.value = false;
  }
}

function updatePagination({ page, pageSize, prop, order }) {
  queryParams.value.page = page;
  queryParams.value.size = pageSize;
  queryParams.value.prop = prop ?? queryParams.value.prop;
  queryParams.value.order = order ?? queryParams.value.order;
  query();
}

function queryWithFilters() {
  queryParams.value.page = 1;
  query();
}

function resetFilters() {
  filters.nameLike = '';
  filters.volumeId = null;
  queryWithFilters();
}

function capacityLabel(row, field) {
  return formatCapacity(row.capacity?.[field], { emptyText: '-' });
}

watch(
  [() => props.clusterId, () => props.resourceType],
  () => {
    queryParams.value = { page: 1, size: 20, prop: undefined, order: undefined };
    filters.nameLike = '';
    filters.volumeId = null;
    query();
  },
  { immediate: true },
);
</script>

<template>
  <section class="cluster-resource-list-tab">
    <QueryForm
      @query="queryWithFilters"
      @reset="resetFilters">
      <ElFormItem
        :label="resource.nameLabel"
        class="query-form-field--wide">
        <ElInput
          v-model="filters.nameLike"
          clearable
          :placeholder="`根据${resource.nameLabel}模糊搜索`" />
      </ElFormItem>
      <ElFormItem
        v-if="resourceType === 'qtree'"
        label="所属存储空间">
        <VolumeSelect
          v-model="filters.volumeId"
          :storage-cluster-id="clusterId"
          :multiple="false"
          clearable />
      </ElFormItem>
    </QueryForm>
    <DataTable
      :pagination="pagination"
      :loading="querying"
      :data="result.content"
      :error="error"
      @update:pagination="updatePagination">
      <template v-if="resourceType === 'aggregate'">
        <ElTableColumn
          :label="resource.nameLabel"
          prop="name"
          min-width="180"
          show-overflow-tooltip>
          <template #default="{ row }">
            <AccessibleResourceLink :to="{ name: resource.detailRoute, params: { id: row.id } }">
              {{ row.name || '-' }}
            </AccessibleResourceLink>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showSecondaryColumns"
          label="原生类型"
          min-width="140">
          <template #default="{ row }">{{ getStorageResourceNativeType('aggregate', row) }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showCapacityColumns"
          label="限额"
          prop="limit"
          sortable="custom"
          min-width="120">
          <template #default="{ row }">
            <span v-if="row.limit != null">{{ capacityLabel(row, 'limit') }}</span>
            <ElTag
              v-else
              type="danger">无硬限额</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showCapacityColumns"
          label="使用量"
          prop="used"
          sortable="custom"
          min-width="120">
          <template #default="{ row }">{{ capacityLabel(row, 'used') }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showSecondaryColumns"
          label="使用率(%)"
          prop="use_ratio"
          sortable="custom"
          min-width="240">
          <template #default="{ row }">
            <Progress
              v-if="canRenderQuotaProgress({ used: row.used, total: row.limit })"
              :used="row.used"
              :total="row.limit"
              :show-numbers="false" />
          </template>
        </ElTableColumn>
      </template>

      <template v-else-if="resourceType === 'volume'">
        <ElTableColumn
          :label="resource.nameLabel"
          prop="name"
          min-width="200"
          show-overflow-tooltip>
          <template #default="{ row }">
            <AccessibleResourceLink :to="{ name: resource.detailRoute, params: { id: row.id } }">
              {{ row.name || '-' }}
            </AccessibleResourceLink>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showSecondaryColumns"
          label="服务域（SVM / Access Zone）"
          prop="vserver"
          min-width="180" />
        <ElTableColumn
          v-if="showCapacityColumns"
          label="所属容量池"
          prop="aggregate"
          min-width="140" />
        <ElTableColumn
          v-if="showSecondaryColumns"
          label="原生类型"
          min-width="150">
          <template #default="{ row }">{{ getStorageResourceNativeType('volume', row) }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showCapacityColumns"
          label="状态"
          prop="state"
          min-width="100" />
        <ElTableColumn
          v-if="showCapacityColumns"
          label="硬限额"
          prop="limit"
          sortable="custom"
          min-width="120">
          <template #default="{ row }">
            <span v-if="row.limit != null">{{ capacityLabel(row, 'limit') }}</span>
            <ElTag
              v-else
              type="danger">无硬限额</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showSecondaryColumns"
          label="软限额"
          prop="soft_limit"
          sortable="custom"
          min-width="120">
          <template #default="{ row }">
            <span v-if="row.soft_limit != null">{{ capacityLabel(row, 'soft_limit') }}</span>
            <ElTag
              v-else
              type="warning">无软限额</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showCapacityColumns"
          label="使用量"
          prop="used"
          sortable="custom"
          min-width="120">
          <template #default="{ row }">{{ capacityLabel(row, 'used') }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showSecondaryColumns"
          label="硬限额使用率(%)"
          prop="use_ratio"
          sortable="custom"
          min-width="240">
          <template #default="{ row }">
            <Progress
              v-if="canRenderQuotaProgress({ used: row.used, total: row.limit })"
              :used="row.used"
              :total="row.limit"
              :show-numbers="false" />
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showSecondaryColumns"
          label="软限额使用率(%)"
          prop="soft_use_ratio"
          sortable="custom"
          min-width="240">
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
      </template>

      <template v-else>
        <ElTableColumn
          :label="resource.nameLabel"
          prop="name"
          min-width="200"
          show-overflow-tooltip>
          <template #default="{ row }">
            <AccessibleResourceLink :to="{ name: resource.detailRoute, params: { id: row.id } }">
              {{ row.name || '-' }}
            </AccessibleResourceLink>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showCapacityColumns"
          label="所属存储空间"
          min-width="180"
          show-overflow-tooltip>
          <template #default="{ row }">
            <AccessibleResourceLink :to="{ name: 'VolumeDetail', params: { id: row.volume?.id } }">
              {{ row.volume?.name || '-' }}
            </AccessibleResourceLink>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showSecondaryColumns"
          label="状态"
          prop="status"
          min-width="100" />
        <ElTableColumn
          v-if="showCapacityColumns"
          label="硬限额"
          prop="limit"
          sortable="custom"
          min-width="120">
          <template #default="{ row }">
            <span v-if="row.limit != null">{{ capacityLabel(row, 'limit') }}</span>
            <ElTag
              v-else
              type="danger">无硬限额</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showSecondaryColumns"
          label="软限额"
          prop="soft_limit"
          sortable="custom"
          min-width="120">
          <template #default="{ row }">
            <span v-if="row.soft_limit != null">{{ capacityLabel(row, 'soft_limit') }}</span>
            <ElTag
              v-else
              type="warning">无软限额</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showCapacityColumns"
          label="使用量"
          prop="used"
          sortable="custom"
          min-width="120">
          <template #default="{ row }">{{ capacityLabel(row, 'used') }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showSecondaryColumns"
          label="硬限额使用率(%)"
          prop="use_ratio"
          sortable="custom"
          min-width="240">
          <template #default="{ row }">
            <Progress
              v-if="canRenderQuotaProgress({ used: row.used, total: row.limit })"
              :used="row.used"
              :total="row.limit"
              :show-numbers="false" />
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="showSecondaryColumns"
          label="软限额使用率(%)"
          prop="soft_use_ratio"
          sortable="custom"
          min-width="240">
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
      </template>
    </DataTable>
  </section>
</template>

<style lang="scss" scoped>
.cluster-resource-list-tab {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  gap: var(--spacing-md);
}

.cluster-resource-list-tab :deep(.data-table-card) {
  flex: 1 1 auto;
  min-height: 0;
  height: auto;
}

.cluster-resource-list-tab :deep(.table-wrapper) {
  overflow-x: hidden;
  overflow-y: auto;
}

.cluster-resource-list-tab :deep(.el-table__body-wrapper) {
  overflow-x: hidden !important;
}

.cluster-resource-list-tab :deep(.el-table .cell) {
  overflow-wrap: anywhere;
  white-space: normal;
}
</style>
