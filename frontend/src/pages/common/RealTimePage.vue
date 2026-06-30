<script setup>
import { ElDatePicker, ElFormItem, ElOption, ElRow, ElSelect, ElCol, ElDescriptions, ElDescriptionsItem, ElCard, ElTable, ElTableColumn, ElTag } from 'element-plus';
import { ref, watch, computed } from 'vue';
import MultipleLineCharts from '@/common/charts/MultipleLineCharts.vue';
import LineCharts from '@/common/charts/LineCharts.vue';
import FilterForm from '@/components/form/QueryForm.vue';
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

const props = defineProps({
  apiType: {
    type: String,
    required: true,
    validator: (value) => ['volume', 'qtree', 'aggregate', 'project', 'storage-usage'].includes(value),
  },
  label: {
    type: String,
    required: true
  },
  attributeId: {
    type: [Number, Array],
  },
});

const attributeId = ref(Array.isArray(props.attributeId) ? props.attributeId : [props.attributeId]);
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

const selectedApi = computed(() => apiMap[props.apiType]);
const selectedSelect = computed(() => selectMap[props.apiType]);
const relatedType = computed(() => relatedTypeMap[props.apiType]);
const { queryParams, reset } = useQueryParams(() => ({
  start_time: dateRange.value[0],
  end_time: dateRange.value[1],
  indicator: 'used',
}));

const indicatorOptions = computed(() => {
  return props.apiType === 'storage-usage' ? { used: '实时使用量', use_ratio: '实时使用率', file_used: '实时文件数量' } : { used: '实时使用量', use_ratio: '实时使用率' };
});

const fetchData = async () => {
  const promises = attributeId.value.map(id =>
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

  return { data, info };
};

const { result, querying, query } = useQuery(fetchData, {
  data: {}
});

// Fetch alerts and merge results
const fetchAlerts = async () => {
  const promises = attributeId.value.map(id =>
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

const shortcuts = [
  { text: '一天内', value: () => getDefaultTime(8) },
  { text: '一周内', value: () => getDefaultTime(24 * 7) },
  { text: '一月内', value: () => getDefaultTime(24 * 30) },
  { text: '三月内', value: () => getDefaultTime(24 * 90) },
];

watch(dateRange, (newVal) => {
  queryParams.value.start_time = newVal[0];
  queryParams.value.end_time = newVal[1];
  query();
  alertQuery();
}, { immediate: true });
// Watch queryParams for changes deeply
watch(() => queryParams, () => {
  query();
  alertQuery();
}, { deep: true });

// Watch attributeId for changes
watch(attributeId, () => {
  query();
  alertQuery();
}, { deep: true });
const yAxisUnit = computed(() => {
  return queryParams.value.indicator === 'used' ? 'G' : queryParams.value.indicator === 'use_ratio' ? '%' : '';
});

</script>
<template>
  <div class="flex flex-col flex-1 min-h-0">
    <FilterForm
      @query="query();alertQuery();"
      @reset="reset(); query();alertQuery();">
      <ElFormItem
        :label="props.label"
        class="w-120">
        <component
          :is="selectedSelect"
          v-model="attributeId"
          :multiple="true" />
      </ElFormItem>
      <ElFormItem
        label="时间范围"
        class="w-120 ml-40">
        <ElDatePicker
          v-model="dateRange"
          type="datetimerange"
          range-separator="至"
          format="YYYY-MM-DD HH:mm:ss"
          value-format="YYYY-MM-DD HH:mm:ss"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :shortcuts="shortcuts"
        />
      </ElFormItem>
      <ElFormItem
        label="指标"
        class="ml-80 w-100">
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
      v-if="attributeId.length === 1"
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
        <ElDescriptionsItem label="限额">{{ result.info?.limit }} G</ElDescriptionsItem>
        <ElDescriptionsItem label="使用量">{{ result.info?.used }} G</ElDescriptionsItem>
        <ElDescriptionsItem label="利用率">{{ result.info?.use_ratio }} %</ElDescriptionsItem>
        <slot
          name="extra-descriptions"
          :info="result.info"></slot>
      </ElDescriptions>
    </ElCard>
    <div class="flex flex-auto mt-2.5">
      <div class="basis-3/4 pr-4">
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
              :text="'NO DATA'"
              :width="'100%'"
              :height="'100%'" />
          </div>
          <div
            v-else-if="attributeId.length === 1"
            class="h-full">
            <LineCharts
              :data="Object.values(result.data)[0]"
              :title="''"
              :is-count="false"
              :width="'100%'"
              :height="'100%'"
              :show-stats="true"
              :y-axis-unit="yAxisUnit"
              :threshold="queryParams.indicator === 'used' ? result.info?.limit * 0.8 : queryParams.indicator === 'use_ratio' ? 80 : null"
              :legend-name="result.info.linux_path ? result.info.linux_path :result.info.name"
            />
          </div>

          <div
            v-else
            class="h-full">
            <MultipleLineCharts
              :data="result.data"
              :title="''"
              :is-count="false"
              :width="'100%'"
              :height="'100%'"
              :y-axis-unit="yAxisUnit"
            />
          </div>
        </ElCard>
      </div>

      <div class="basis-1/4">
        <ElCard class="h-full">
          <ElTable
            :data="alertResult.content"
            style="width: 100%; height: 100%;"
            :loading="alertQuerying">
            <ElTableColumn
              prop="description"
              label="提示"
              min-width="180"
              :show-overflow-tooltip="true">
              <template #default="{ row }">
                <div class="ellipsis-text">{{ row.description }}</div>
              </template>
            </ElTableColumn>
            <ElTableColumn
              label="触发值"
              min-width="60">
              <template #default="{ row }">
                <ElTag :type="row.alert_level==='high'?'danger':row.alert_level==='medium'?'warning':'success'">
                  {{ row.avg_use_ratio }}
                </ElTag>
              </template>
            </ElTableColumn>
            <ElTableColumn
              prop="updated_at"
              label="时间"
              min-width="130" />
          </ElTable>
        </ElCard>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';

:deep(.el-card) {
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

// 表格样式
:deep(.el-table) {
  border-radius: var(--radius-md);
  overflow: hidden;
  font-size: var(--font-size-sm);

  .el-table__header-wrapper {
    .el-table__header {
      thead {
        tr {
          th {
            background: var(--bg-secondary);
            color: var(--text-primary);
            font-weight: var(--font-weight-semibold);
            border-bottom: 1px solid var(--border-color);
          }
        }
      }
    }
  }

  .el-table__body-wrapper {
    .el-table__body {
      tbody {
        tr {
          transition: var(--transition-base);

          &:hover {
            background: var(--bg-hover) !important;
          }

          td {
            border-bottom: 1px solid var(--border-light);
            color: var(--text-secondary);
          }
        }
      }
    }
  }

  .el-table__empty-block {
    padding: var(--spacing-4xl) 0;

    .el-table__empty-text {
      color: var(--text-tertiary);
      font-size: var(--font-size-sm);
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
