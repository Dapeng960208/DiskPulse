<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { ElDatePicker, ElFormItem, ElOption, ElSelect, ElTag } from 'element-plus';
import { useRoute } from 'vue-router';
import FilterForm from '@/components/form/QueryForm.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import AnimatedTextChart from '@/common/charts/AnimatedTextChart.vue';
import StorageTrendChart from '@/components/dashboard/StorageTrendChart.vue';
import { getDefaultTime } from '@/composables/common';
import volumeApi from '@/api/volume-api.js';
import { useBreadcrumbs } from '@/stores/breadcrumbs';

const route = useRoute();
const breadcrumbs = useBreadcrumbs();
const volumeId = computed(() => Number(route.params.id));
const dateRange = ref(getDefaultTime(8));
const selectedMetrics = ref(['latency_total', 'iops_total', 'throughput_total']);
const monitoring = ref({ info: null, binding: null, capacity: [], performance: [] });
const loading = ref(false);

const metricOptions = [
  { value: 'latency_read', label: '读延迟' },
  { value: 'latency_write', label: '写延迟' },
  { value: 'latency_total', label: '总延迟' },
  { value: 'iops_total', label: 'IOPS' },
  { value: 'throughput_total', label: '吞吐量' },
];
const metricLabels = Object.fromEntries(metricOptions.map((item) => [item.value, item.label]));
const performanceByMetric = computed(() => new Map((monitoring.value.performance || []).map((item) => [item.metric, item])));
const capacitySeries = computed(() => [{ name: '已用容量', data: monitoring.value.capacity || [] }]);

function metricSeries(metric) {
  const item = performanceByMetric.value.get(metric);
  return [{ name: metricLabels[metric], data: item?.data || [] }];
}

function metricState(metric) {
  return performanceByMetric.value.get(metric) || { unit: '', status: 'empty', match_source: 'unmatched' };
}

async function load() {
  if (!Number.isInteger(volumeId.value) || volumeId.value <= 0) return;
  loading.value = true;
  try {
    const result = await volumeApi.fetchMonitoring(volumeId.value, {
      start_time: dateRange.value?.[0],
      end_time: dateRange.value?.[1],
      metrics: selectedMetrics.value,
    });
    monitoring.value = {
      info: null,
      binding: null,
      capacity: [],
      performance: [],
      ...(result && typeof result === 'object' ? result : {}),
    };
    breadcrumbs.setDetailTitle(route.name, monitoring.value.info?.name || '');
  } finally {
    loading.value = false;
  }
}

watch(dateRange, load, { deep: true });
onMounted(load);
</script>

<template>
  <section class="volume-monitoring-page">
    <header class="volume-monitoring-page__header">
      <h1>存储空间性能监控</h1>
      <p>查看存储空间容量变化和关联存储集群的实时性能指标。</p>
    </header>
    <FilterForm
      @query="load"
      @reset="load">
      <ElFormItem label="存储空间名">
        <div class="volume-monitoring-page__resource-name">{{ monitoring.info?.name || '-' }}</div>
      </ElFormItem>
      <ElFormItem
        label="时间范围"
        class="query-form-field--date-range">
        <ElDatePicker
          v-model="dateRange"
          type="datetimerange"
          range-separator="至"
          value-format="YYYY-MM-DD HH:mm:ss" />
      </ElFormItem>
      <ElFormItem label="性能指标">
        <ElSelect
          v-model="selectedMetrics"
          multiple
          collapse-tags
          collapse-tags-tooltip
          :multiple-limit="5">
          <ElOption
            v-for="option in metricOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value" />
        </ElSelect>
      </ElFormItem>
    </FilterForm>

    <div
      v-if="monitoring.binding"
      class="volume-monitoring-page__binding">
      <span>关联项目目录</span><ElTag type="primary">{{ monitoring.binding.project_name }} / {{ monitoring.binding.linux_path || monitoring.binding.group_name }}</ElTag>
      <span>存储集群</span><ElTag effect="plain">{{ monitoring.info?.storage_cluster?.name || '-' }}</ElTag>
    </div>
    <div
      v-else
      class="volume-monitoring-page__binding volume-monitoring-page__binding--empty">未关联项目目录；仍可查看存储空间容量与性能采集数据。</div>

    <section class="volume-monitoring-page__section">
      <div class="volume-monitoring-page__section-heading"><h2>容量变化</h2><span>已用容量（G）</span></div>
      <div class="volume-monitoring-page__chart-card volume-monitoring-page__chart-card--capacity">
        <LoadingCharts
          v-if="loading"
          width="100%"
          height="360px" />
        <AnimatedTextChart
          v-else-if="capacitySeries[0].data.length === 0"
          text="暂无容量趋势数据"
          width="100%"
          height="360px" />
        <StorageTrendChart
          v-else
          :series="capacitySeries"
          indicator="used"
          unit="G"
          aria-label="存储空间容量变化"
          height="360px" />
      </div>
    </section>

    <section class="volume-monitoring-page__section">
      <div class="volume-monitoring-page__section-heading"><h2>实时性能</h2><span>每项指标独立成图，避免混合量纲。</span></div>
      <div class="performance-grid">
        <div
          v-for="metric in selectedMetrics"
          :key="metric"
          class="volume-monitoring-page__chart-card">
          <div class="volume-monitoring-page__chart-title"><h3>{{ metricLabels[metric] }}</h3><span>{{ metricState(metric).unit }}</span></div>
          <AnimatedTextChart
            v-if="!loading && metricState(metric).status !== 'data'"
            text="该时间范围暂无性能数据"
            width="100%"
            height="280px" />
          <LoadingCharts
            v-else-if="loading"
            width="100%"
            height="280px" />
          <StorageTrendChart
            v-else
            :series="metricSeries(metric)"
            :indicator="metric"
            :unit="metricState(metric).unit"
            :aria-label="`${metricLabels[metric]}趋势`"
            height="280px" />
        </div>
      </div>
    </section>
  </section>
</template>

<style lang="scss" scoped>
.volume-monitoring-page { display: flex; flex: 1; min-width: 0; flex-direction: column; gap: var(--spacing-md); }
.volume-monitoring-page__header h1 { font-size: var(--font-size-2xl); }
.volume-monitoring-page__header p, .volume-monitoring-page__section-heading span { margin-top: 4px; color: var(--text-secondary); font-size: var(--font-size-sm); }
.volume-monitoring-page__resource-name { min-width: 220px; padding: 0 11px; color: var(--text-secondary); }
.volume-monitoring-page__binding { display: flex; flex-wrap: wrap; align-items: center; gap: var(--spacing-sm); padding: var(--spacing-sm) var(--spacing-md); border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-primary); color: var(--text-secondary); }
.volume-monitoring-page__binding--empty { color: var(--text-tertiary); }
.volume-monitoring-page__section { display: flex; flex-direction: column; gap: var(--spacing-sm); }
.volume-monitoring-page__section-heading { display: flex; align-items: baseline; gap: var(--spacing-sm); }
.volume-monitoring-page__section-heading span { margin: 0; }
.volume-monitoring-page__chart-card { min-width: 0; padding: var(--spacing-md); border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-primary); }
.volume-monitoring-page__chart-title { display: flex; justify-content: space-between; margin-bottom: var(--spacing-xs); }.volume-monitoring-page__chart-title h3 { font-size: var(--font-size-base); }.volume-monitoring-page__chart-title span { color: var(--text-tertiary); font-size: var(--font-size-sm); }
.performance-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--spacing-md); }
@media (max-width: 768px) { .performance-grid { grid-template-columns: 1fr; } }
</style>
