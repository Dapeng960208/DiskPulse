<script setup>
import {
  ElButton,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElFormItem,
  ElMessage,
  ElOption,
  ElSelect,
  ElTableColumn,
} from 'element-plus';
import { computed, ref, watch } from 'vue';
import FilterForm from '@/components/form/QueryForm.vue';
import TimeRangePicker from '@/components/form/TimeRangePicker.vue';
import BarStackChart from '@/common/charts/BarStackChart.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import DataTable from '@/components/data/DataTable.vue';
import storageClusterApi from '@/api/storage-cluster-api';
import { useClusterExport } from '@/composables/useClusterExport';

const props = defineProps({
  clusterId: { type: Number, required: true },
  dateRange: { type: Array, required: true },
});

const emit = defineEmits(['update:dateRange']);

const localDateRange = computed({
  get: () => props.dateRange,
  set: (value) => emit('update:dateRange', value),
});

const latency = ref({ supported: true, data: [] });
const loading = ref(false);
const performanceLimit = ref(10);
const selectedPerformanceObjects = ref([]);
const selectedPerformanceMetrics = ref(['p95_latency']);

const performanceMetricOptions = [
  { key: 'p95_latency', label: 'P95 延迟', unit: 'ms' },
  { key: 'avg_latency', label: '平均延迟', unit: 'ms' },
  { key: 'max_latency', label: '最大延迟', unit: 'ms' },
  { key: 'avg_read_latency', label: '平均读延迟', unit: 'ms' },
  { key: 'avg_write_latency', label: '平均写延迟', unit: 'ms' },
  { key: 'avg_iops', label: '平均 IOPS', unit: 'IOPS' },
  { key: 'avg_throughput', label: '平均吞吐量', unit: 'B/s' },
];

const latencyData = computed(() => latency.value?.data || []);
const performanceObjectOptions = computed(() => {
  const uniqueOptions = new Map();
  latencyData.value.forEach((item) => {
    const value = item.object_id || item.object_name;
    if (value && !uniqueOptions.has(value)) {
      uniqueOptions.set(value, { value, label: item.object_name || item.object_id });
    }
  });
  return [...uniqueOptions.values()];
});
const filteredLatencyData = computed(() => {
  if (selectedPerformanceObjects.value.length === 0) return latencyData.value;
  return latencyData.value.filter((item) => selectedPerformanceObjects.value.includes(
    item.object_id || item.object_name,
  ));
});
const latencyCategories = computed(() => filteredLatencyData.value.map((item) => item.object_name || item.object_id || '-'));
const selectedPerformanceMetricOptions = computed(() => performanceMetricOptions.filter(
  ({ key }) => selectedPerformanceMetrics.value.includes(key),
));
const performanceCharts = computed(() => selectedPerformanceMetricOptions.value.map((metric) => ({
  ...metric,
  data: [filteredLatencyData.value.map((item) => Number(item[metric.key]) || 0)],
})));

const { handleExport } = useClusterExport({
  clusterId: computed(() => props.clusterId),
  dateRange: localDateRange,
  defaultSection: 'latency',
});

async function load() {
  if (!props.clusterId) return;
  loading.value = true;
  try {
    latency.value = await storageClusterApi.fetchTopLatency(props.clusterId, {
      start_time: localDateRange.value?.[0],
      end_time: localDateRange.value?.[1],
      object_type: 'volume',
      limit: performanceLimit.value,
    });
  } catch {
    latency.value = { supported: true, data: [] };
    ElMessage.error('加载性能数据失败，请稍后重试');
  } finally {
    loading.value = false;
  }
}

function search() {
  load();
}

function reset() {
  performanceLimit.value = 10;
  selectedPerformanceObjects.value = [];
  selectedPerformanceMetrics.value = ['p95_latency'];
  emit('update:dateRange', props.dateRange);
  load();
}

watch(() => props.clusterId, load, { immediate: true });
watch(() => props.dateRange, load);
watch(performanceObjectOptions, (options) => {
  const availableValues = new Set(options.map((option) => option.value));
  selectedPerformanceObjects.value = selectedPerformanceObjects.value.filter(
    (value) => availableValues.has(value),
  );
});
</script>

<template>
  <section class="cluster-performance-tab">
    <FilterForm
      class="performance-filter"
      @query="search"
      @reset="reset">
      <ElFormItem
        label="时间范围"
        class="analytics-date-range query-form-field--date-range">
        <!-- Keep every time-based analytics tab on the backend range contract. -->
        <TimeRangePicker
          v-model="localDateRange"
          :max-days="180" />
      </ElFormItem>
      <ElFormItem
        label="展示条数"
        class="performance-limit">
        <ElSelect v-model="performanceLimit">
          <ElOption
            v-for="limit in [10, 20, 50, 100]"
            :key="limit"
            :label="`${limit} 条`"
            :value="limit" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem
        label="性能指标"
        class="performance-metrics">
        <ElSelect
          v-model="selectedPerformanceMetrics"
          multiple
          collapse-tags
          collapse-tags-tooltip>
          <ElOption
            v-for="metric in performanceMetricOptions"
            :key="metric.key"
            :label="metric.label"
            :value="metric.key" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem
        label="对象"
        class="performance-objects">
        <ElSelect
          v-model="selectedPerformanceObjects"
          multiple
          clearable
          collapse-tags
          collapse-tags-tooltip
          filterable
          placeholder="选择对象进行对比">
          <ElOption
            v-for="object in performanceObjectOptions"
            :key="object.value"
            :label="object.label"
            :value="object.value" />
        </ElSelect>
      </ElFormItem>
      <template #actions>
        <ElDropdown @command="handleExport">
          <ElButton type="primary">导出报告</ElButton>
          <template #dropdown>
            <ElDropdownMenu>
              <ElDropdownItem command="current:csv">当前页 CSV</ElDropdownItem>
              <ElDropdownItem command="current:excel">当前页 Excel</ElDropdownItem>
              <ElDropdownItem command="current:pdf">当前页 PDF</ElDropdownItem>
              <ElDropdownItem
                divided
                command="all:csv">完整报告 CSV</ElDropdownItem>
              <ElDropdownItem command="all:excel">完整报告 Excel</ElDropdownItem>
              <ElDropdownItem command="all:pdf">完整报告 PDF</ElDropdownItem>
            </ElDropdownMenu>
          </template>
        </ElDropdown>
      </template>
    </FilterForm>
    <LoadingCharts
      v-if="loading"
      width="100%"
      height="360px" />
    <div
      v-else-if="latency.supported === false"
      class="analytics-empty">尚未采集到性能数据，请检查采集任务和设备 API 权限</div>
    <div
      v-else-if="!latencyData.length"
      class="analytics-empty">当前时间范围内暂无性能数据</div>
    <div v-else>
      <div class="performance-charts">
        <BarStackChart
          v-for="metric in performanceCharts"
          :key="metric.key"
          :data="metric.data"
          :categories="latencyCategories"
          :series-names="[metric.key]"
          :series-map="{ [metric.key]: metric.label }"
          :title="`${metric.label}（最多 ${performanceLimit} 条）`"
          :unit="metric.unit"
          width="100%"
          height="360px" />
      </div>
      <DataTable :data="filteredLatencyData">
        <ElTableColumn
          label="对象"
          prop="object_name" />
        <ElTableColumn
          label="类型"
          prop="object_type" />
        <ElTableColumn
          v-for="metric in selectedPerformanceMetricOptions"
          :key="metric.key"
          :label="`${metric.label}(${metric.unit})`"
          :prop="metric.key" />
        <ElTableColumn
          label="样本数"
          prop="sample_count" />
      </DataTable>
    </div>
  </section>
</template>

<style scoped>
.cluster-performance-tab {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.performance-filter {
  margin-bottom: var(--spacing-md);
}

.performance-filter :deep(.analytics-date-range .el-date-editor) {
  width: 100%;
}

.analytics-empty {
  display: grid;
  min-height: 360px;
  place-items: center;
  color: var(--el-text-color-secondary);
}

.performance-charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 480px), 1fr));
  gap: var(--spacing-md);
}
</style>
