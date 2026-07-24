<script setup>
import { ElFormItem, ElOption, ElSelect, ElDescriptions, ElDescriptionsItem, ElCard, ElTableColumn, ElTag } from 'element-plus';
import { ref, watch, computed } from 'vue';
import DataTable from '@/components/data/DataTable.vue';
import { useRoute } from 'vue-router';
import StorageTrendChart from '@/components/dashboard/StorageTrendChart.vue';
import FilterForm from '@/components/form/QueryForm.vue';
import TimeRangePicker from '@/components/form/TimeRangePicker.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import QtreeSelect from '@/components/form/QtreeSelect.vue';
import VolumeSelect from '@/components/form/VolumeSelect.vue';
import AggregateSelect from '@/components/form/AggregateSelect.vue';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import StorageUsageSelect from '@/components/form/StorageUsageSelect.vue';
import AnimatedTextChart from '@/common/charts/AnimatedTextChart.vue';
import GroupSelect from '@/components/form/GroupSelect.vue';
import RdUserSelect from '@/components/form/RdUserSelect.vue';
import groupApi from '@/api/group-api.js';
import qtreeApi from '@/api/qtree-api.js';
import volumeApi from '@/api/volume-api.js';
import alertApi from '@/api/alert-api.js';
import aggregateApi from '@/api/aggregate-api.js';
import projectApi from '@/api/project-api.js';
import storageUsageApi from '@/api/storage-usage-api.js';
import { getDefaultTime } from '@/composables/common';
import { useQuery, useQueryParams } from '@/composables/query';
import { useStorageAlertThresholds } from '@/stores/storage-alert-thresholds';
import { useBreadcrumbs } from '@/stores/breadcrumbs';
import { formatCapacity } from '@/utils/capacity';
import { toUtcRange } from '@/utils/datetime.js';

const props = defineProps({
  apiType: {
    type: String,
    required: true,
    validator: (value) => [
      'volume',
      'qtree',
      'aggregate',
      'project',
      'group',
      'storage-usage',
    ].includes(value),
  },
  label: {
    type: String,
    required: true
  },
  attributeId: {
    type: [Number, Array],
  },
  showHeader: {
    type: Boolean,
    default: true,
  },
  showResourceSelect: {
    type: Boolean,
    default: true,
  },
  allowedIndicators: {
    type: Array,
    default: null,
  },
  fillContent: {
    type: Boolean,
    default: false,
  },
});

function normalizeResourceIds(value) {
  return (Array.isArray(value) ? value : [value])
    .map(Number)
    .filter((id) => Number.isInteger(id) && id > 0);
}

const attributeId = ref(normalizeResourceIds(props.attributeId));
const route = useRoute();
const breadcrumbs = useBreadcrumbs();
const dateRange = ref(getDefaultTime(8));

const apiMap = {
  volume: volumeApi,
  qtree: qtreeApi,
  aggregate: aggregateApi,
  project: projectApi,
  group: groupApi,
  'storage-usage': storageUsageApi
};

const selectMap = {
  volume: VolumeSelect,
  qtree: QtreeSelect,
  aggregate: AggregateSelect,
  project: ProjectSelect,
  group: GroupSelect,
  'storage-usage': StorageUsageSelect
};

const relatedTypeMap = {
  volume: 'Volume',
  qtree: 'Qtree',
  aggregate: 'Aggregate',
  project: 'Project',
  group: 'Group',
  'storage-usage': 'StorageUsage',
};

const alertLevelLabels = {
  important: '重要',
  serious: '严重',
  emergency: '紧急',
  high: '高',
  medium: '中',
  low: '低',
};

const alertLevelType = (level) => {
  if (['emergency', 'serious', 'high'].includes(level)) return 'danger';
  if (['important', 'medium'].includes(level)) return 'warning';
  return 'info';
};

const alertLevelLabel = (level) => alertLevelLabels[level] || level || '-';

const selectedApi = computed(() => apiMap[props.apiType]);
const selectedSelect = computed(() => selectMap[props.apiType]);
const relatedType = computed(() => relatedTypeMap[props.apiType]);
const resourceIds = computed(() => attributeId.value
  .map(Number)
  .filter((id) => Number.isInteger(id) && id > 0));
const alertThresholds = useStorageAlertThresholds();
alertThresholds.load();
const { queryParams, reset } = useQueryParams(() => ({
  start_time: toUtcRange(dateRange.value)[0],
  end_time: toUtcRange(dateRange.value)[1],
  indicator: 'used',
}));

const indicatorOptions = computed(() => {
  const common = { used: '实时使用量', alert_ratio: '告警口径使用率', use_ratio: '硬限额使用率' };
  const options = props.apiType === 'storage-usage' ? { ...common, file_used: '实时文件数量' } : common;
  if (!props.allowedIndicators) return options;
  return Object.fromEntries(
    Object.entries(options).filter(([value]) => props.allowedIndicators.includes(value)),
  );
});

const fetchData = async () => {
  if (resourceIds.value.length === 0) return { data: {}, info: {}, trend_meta: null, data_unit: null };
  const promises = resourceIds.value.map(id =>
    selectedApi.value.fetchStorageRealTimeDataById(id, queryParams.value)
  );

  const results = await Promise.all(promises);
  const data = results.reduce((acc, result) => {
    if(props.apiType==='storage-usage'){
      acc[result.info.linux_path] = result.data;
    }else{
      acc[result.info.name] = result.data;
    }

    return acc;
  }, {});
  const info = results[0]?.info ?? {};

  return {
    data,
    info,
    trend_meta: results[0]?.trend_meta ?? null,
    data_unit: results[0]?.data_unit ?? null,
  };
};

const { result, querying, query } = useQuery(fetchData, {
  data: {}
});

const breadcrumbDetailTitle = computed(() => {
  if (props.apiType === 'storage-usage') {
    return result.value?.info?.user?.rd_username
      || result.value?.info?.linux_path?.split('/').filter(Boolean).at(-1)
      || '';
  }
  return result.value?.info?.name || '';
});

watch(breadcrumbDetailTitle, (title) => {
  breadcrumbs.setDetailTitle(route.name, title);
}, { immediate: true });

// Fetch alerts and merge results
const fetchAlerts = async () => {
  if (resourceIds.value.length === 0) return { content: [] };
  const promises = resourceIds.value.map(id =>
    alertApi.fetch({ 'related_type': relatedType.value, 'related_id': id })
  );

  const results = await Promise.all(promises);
  // Flatten results and sort by updated_at in descending order
  const allAlerts = results.flatMap(result => result.content).sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));

  // Return top 20 alerts
  return { content: allAlerts.slice(0, 20) };
};

const { result: alertResult, querying: alertQuerying, query: alertQuery } = useQuery(fetchAlerts, {
  content: []
});

watch(dateRange, (newVal) => {
  const [startTime, endTime] = toUtcRange(newVal);
  queryParams.value.start_time = startTime;
  queryParams.value.end_time = endTime;
  query();
  alertQuery();
}, { immediate: true });
// Watch queryParams for changes deeply
watch(queryParams, () => {
  query();
  alertQuery();
}, { deep: true });

// Watch attributeId for changes
watch(attributeId, () => {
  query();
  alertQuery();
}, { deep: true });
watch(() => props.attributeId, (value) => {
  attributeId.value = normalizeResourceIds(value);
}, { deep: true });
const yAxisUnit = computed(() => {
  if (result.value?.data_unit === 'count') return '个';
  if (result.value?.data_unit) return result.value.data_unit;
  return queryParams.value.indicator === 'used' ? 'GB' : ['use_ratio', 'alert_ratio'].includes(queryParams.value.indicator) ? '%' : '';
});
const trendSeries = computed(() => Object.entries(result.value.data || {}).map(([name, data]) => ({ name, data })));
const systemThresholds = computed(() => resourceIds.value.length > 1 ? alertThresholds.thresholds : null);

</script>
<template>
  <div
    class="real-time-page flex flex-col flex-1 min-h-0"
    :class="{ 'real-time-page--fill': fillContent }">
    <section
      v-if="showHeader"
      class="real-time-page__header">
      <div>
        <h1>{{ props.label }}实时监控</h1>
      </div>
    </section>
    <FilterForm
      @query="query();alertQuery();"
      @reset="reset(); query();alertQuery();">
      <ElFormItem
        v-if="showResourceSelect && selectedSelect"
        :label="props.label">
        <component
          :is="selectedSelect"
          v-model="attributeId"
          :multiple="true" />
      </ElFormItem>
      <ElFormItem
        label="时间范围"
        class="query-form-field--date-range">
        <TimeRangePicker v-model="dateRange" />
      </ElFormItem>
      <ElFormItem label="指标">
        <ElSelect
          v-model="queryParams.indicator"
          collapse-tags
          collapse-tags-tooltip>
          <ElOption
            v-for="(label, value) in indicatorOptions"
            :key="value"
            :label="label"
            :value="value" />
        </ElSelect>
      </ElFormItem>
    </FilterForm>

    <ElCard
      v-if="resourceIds.length === 1"
      class="mt-2.5">
      <ElDescriptions
        :column="4"
        size="large"
        border>
        <ElDescriptionsItem
          v-if="props.apiType==='storage-usage'"
          :label="props.label">{{ result.info?.linux_path }}</ElDescriptionsItem>
        <ElDescriptionsItem
          v-else
          :label="props.label">{{ result.info?.name }}</ElDescriptionsItem>
        <ElDescriptionsItem label="限额">{{ formatCapacity(result.info?.capacity?.limit, { emptyText: '无硬限额' }) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="使用量">{{ formatCapacity(result.info?.capacity?.used) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="利用率">{{ result.info?.use_ratio }} %</ElDescriptionsItem>
        <slot
          name="extra-descriptions"
          :info="result.info"></slot>
      </ElDescriptions>
    </ElCard>
    <div class="real-time-page__workspace flex flex-auto mt-2.5">
      <div class="real-time-page__chart-panel basis-3/4 pr-4">
        <ElCard class="h-full">
          <div
            v-if="querying"
            class="h-full">
            <LoadingCharts
              :width="'100%'"
              :height="'100%'" />
          </div>
          <div
            v-else-if="!result.data || Object.keys(result.data).length === 0"
            class="h-full">
            <AnimatedTextChart
              :text="'暂无趋势数据'"
              :width="'100%'"
              :height="'100%'" />
          </div>
          <StorageTrendChart
            v-else
            :series="trendSeries"
            :indicator="queryParams.indicator"
            :trend-meta="result.trend_meta"
            :system-thresholds="systemThresholds"
            :unit="yAxisUnit"
            :aria-label="`${props.label}容量趋势`"
            height="100%" />
        </ElCard>
      </div>

      <div class="real-time-page__alerts-panel basis-1/4">
        <DataTable
          :data="alertResult.content"
          :loading="alertQuerying"
          density="compact">
          <ElTableColumn
            label="告警紧急程度"
            min-width="100"
            align="center">
            <template #default="{ row }">
              <ElTag :type="alertLevelType(row.alert_level)">
                {{ alertLevelLabel(row.alert_level) }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn
            label="触发值"
            min-width="60">
            <template #default="{ row }">
              <ElTag :type="alertLevelType(row.alert_level)">
                {{ row.avg_use_ratio }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn
            prop="updated_at"
            label="时间"
            min-width="130" />
        </DataTable>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';

.real-time-page > :deep(.el-card),
.real-time-page__chart-panel > :deep(.el-card) {
  @include card-base;
  border: 1px solid var(--border-color);

  &:hover {
    border-color: var(--border-dark);
  }

  .el-card__body {
    height: 100%;
    padding: var(--spacing-lg);
  }
}

.real-time-page__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-md);

  h1 {
    font-size: var(--font-size-2xl);
    color: var(--text-primary);
    margin-bottom: var(--spacing-xs);
  }

  p {
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
  }

  span {
    white-space: nowrap;
  }
}

.real-time-filter-field {
  min-width: 240px;

  &--wide {
    min-width: 360px;
  }
}

// 描述列表样式
:deep(.el-descriptions) {
  .el-descriptions__header {
    margin-bottom: var(--spacing-lg);
  }

  .el-descriptions__table {
    border-radius: var(--radius-md);
    overflow: hidden;

    .el-descriptions__cell {
      padding: var(--spacing-md) var(--spacing-lg);
      font-size: var(--font-size-sm);

      &.is-bordered-label {
        background: var(--bg-secondary);
        color: var(--text-primary);
        font-weight: var(--font-weight-medium);
      }

      &.is-bordered-content {
        background: var(--bg-primary);
        color: var(--text-secondary);
      }
    }
  }
}

// 标签样式
:deep(.el-tag) {
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  padding: 4px 8px;

  &.el-tag--success {
    background: var(--success-bg);
    color: var(--success-color);
    border-color: var(--success-color);
  }

  &.el-tag--warning {
    background: var(--warning-bg);
    color: var(--warning-color);
    border-color: var(--warning-color);
  }

  &.el-tag--danger {
    background: var(--danger-bg);
    color: var(--danger-color);
    border-color: var(--danger-color);
  }
}

.ellipsis-text {
  @include text-ellipsis;
}

// 布局优化
.flex {
  &.flex-col {
    gap: var(--spacing-md);
  }

  &.flex-auto {
    gap: var(--spacing-lg);
  }
}

.real-time-page--fill {
  height: 100%;
  min-height: 0;

  .real-time-page__workspace {
    flex: 1 1 0;
    min-height: 0;
  }

  .real-time-page__chart-panel,
  .real-time-page__alerts-panel {
    display: flex;
    min-height: 0;
  }

  .real-time-page__chart-panel :deep(.el-card),
  .real-time-page__alerts-panel :deep(.el-card) {
    flex: 1 1 auto;
    min-height: 0;
  }
}

// 响应式设计
@include mobile {
  .flex.flex-auto {
    flex-direction: column;

    .basis-3\/4,
    .basis-1\/4 {
      flex-basis: auto;
    }

    .pr-4 {
      padding-right: 0;
    }
  }
}

@include tablet {
  .flex.flex-auto {
    .basis-3\/4 {
      flex-basis: 65%;
    }

    .basis-1\/4 {
      flex-basis: 35%;
    }
  }
}
</style>
