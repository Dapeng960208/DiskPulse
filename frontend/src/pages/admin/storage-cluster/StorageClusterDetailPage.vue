<script setup>
import {
  ElButton,
  ElCard,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElPagination,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
  ElTabPane,
  ElTabs,
  ElTooltip,
} from 'element-plus';
import { computed, defineAsyncComponent, onBeforeMount, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import FilterForm from '@/components/form/QueryForm.vue';
import StorageTrendChart from '@/components/dashboard/StorageTrendChart.vue';
import PieCharts from '@/common/charts/PieCharts.vue';
import BarStackChart from '@/common/charts/BarStackChart.vue';
import DiskUsage from '@/common/charts/DiskUsage.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import aggregateApi from '@/api/aggregate-api.js';
import storageClusterApi from '@/api/storage-cluster-api';
import { useQuery } from '@/composables/query';
import { getDefaultTime } from '@/composables/common';
import { useBreadcrumbs } from '@/stores/breadcrumbs';
import { formatCapacity } from '@/utils/capacity';
import TableActionButton from '@/components/basic/TableActionButton.vue';
const ClusterIncidentsTab = defineAsyncComponent(() => import('./components/ClusterIncidentsTab.vue'));
const ClusterResourceListTab = defineAsyncComponent(() => import('./components/ClusterResourceListTab.vue'));
const CapacityExhaustionRiskPanel = defineAsyncComponent(() => import('@/pages/capacity-prediction/CapacityExhaustionRiskPanel.vue'));

const route = useRoute();
const breadcrumbs = useBreadcrumbs();
const clusterId = ref(null);
const dateRange = ref(getDefaultTime(8));
const activeTab = ref('capacity');
const capacity = ref({ data: [] });
const latency = ref({ supported: true, data: [] });
const performanceLimit = ref(10);
const selectedPerformanceObjects = ref([]);
const selectedPerformanceMetrics = ref(['p95_latency']);
const resourceTabNames = ['aggregates', 'volumes', 'qtrees'];
const severity = ref({ counts: {}, total: 0, sources: {} });
const faults = ref({ data: [] });
const systemEvents = ref({ data: [] });
const systemEventDetail = ref(null);
const systemEventDetailVisible = ref(false);
const systemEventFilters = reactive({ keyword: '', severity: '' });
const systemEventPagination = reactive({ page: 1, pageSize: 20, total: 0 });
const loaded = reactive({ capacity: false, distribution: false, performance: false, faults: false });
const loading = reactive({
  capacity: false,
  performance: false,
  faults: false,
  systemEvents: false,
  systemEventDetail: false,
});

const shortcuts = [
  { text: '一天内', value: () => getDefaultTime(8) },
  { text: '一周内', value: () => getDefaultTime(24 * 7) },
  { text: '一月内', value: () => getDefaultTime(24 * 30) },
  { text: '三月内', value: () => getDefaultTime(24 * 90) },
];

const performanceMetricOptions = [
  { key: 'p95_latency', label: 'P95 延迟', unit: 'ms' },
  { key: 'avg_latency', label: '平均延迟', unit: 'ms' },
  { key: 'max_latency', label: '最大延迟', unit: 'ms' },
  { key: 'avg_read_latency', label: '平均读延迟', unit: 'ms' },
  { key: 'avg_write_latency', label: '平均写延迟', unit: 'ms' },
  { key: 'avg_iops', label: '平均 IOPS', unit: 'IOPS' },
  { key: 'avg_throughput', label: '平均吞吐量', unit: 'B/s' },
];

const queryParams = () => ({
  start_time: dateRange.value?.[0],
  end_time: dateRange.value?.[1],
});

const systemEventQueryParams = () => ({
  ...queryParams(),
  ...(systemEventFilters.keyword.trim() ? { keyword: systemEventFilters.keyword.trim() } : {}),
  ...(systemEventFilters.severity ? { severity: systemEventFilters.severity } : {}),
  page: systemEventPagination.page,
  page_size: systemEventPagination.pageSize,
});

const capacityData = computed(() => capacity.value?.data || []);
const capacityChartData = computed(() => capacityData.value.map((item) => [item.updated_at, Number(item.used)]));
const capacityUnit = computed(() => capacity.value?.data_unit || 'TB');
const capacityLabel = (field) => formatCapacity(capacity.value?.capacity?.[field]);
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
const faultData = computed(() => faults.value?.data || []);
const systemEventData = computed(() => systemEvents.value?.data || []);

function hasReviewedVendorSemantics(event) {
  return event?.review_status === 'reviewed'
    && Boolean(event?.association_type)
    && event.association_type !== 'unknown';
}

function vendorEventTitle(event) {
  if (!hasReviewedVendorSemantics(event)) return '待审核 · 未分类厂商事件';
  return event.title_zh || '未收录的厂商事件代码';
}

function vendorEventAssociationLabel(event) {
  if (!hasReviewedVendorSemantics(event)) return '未分类厂商事件';
  return event.association_type_label || '未分类厂商事件';
}

function vendorEventAssociationTagType(event) {
  if (!hasReviewedVendorSemantics(event)) return 'info';
  if (event.association_type === 'fault_log') return 'danger';
  if (event.association_type === 'performance_anomaly') return 'warning';
  return 'info';
}

function vendorEventReviewLabel(event) {
  return hasReviewedVendorSemantics(event) ? '已审核' : '待审核';
}

function vendorEventDescription(event) {
  if (!hasReviewedVendorSemantics(event)) {
    return '该事件代码尚未完成审核，不能根据候选定义推断系统问题；请结合规范化日志和厂商文档核查。';
  }
  return event.description_zh || '该代码尚未维护中文说明，请结合规范化日志核查。';
}

function vendorEventRecommendedSolution(event) {
  if (!hasReviewedVendorSemantics(event)) return '暂无可核验官方方案';
  return event.recommended_solution_zh || '暂无可核验官方方案';
}

const severityChartData = computed(() => [
  ['严重', Number(severity.value?.counts?.critical) || 0],
  ['错误', Number(severity.value?.counts?.error) || 0],
  ['警告', Number(severity.value?.counts?.warning) || 0],
  ['信息', Number(severity.value?.counts?.info) || 0],
].filter(([, count]) => count > 0));

const fetchClusterInfo = async () => {
  if (!clusterId.value) return {};
  return storageClusterApi.fetchById(clusterId.value);
};
const { result: infoResult, query: queryInfo } = useQuery(fetchClusterInfo, {});
watch(() => infoResult.value?.name, (name) => {
  breadcrumbs.setDetailTitle(route.name, name);
}, { immediate: true });
const capacitySeries = computed(() => [{
  name: infoResult.value?.name || '已使用',
  data: capacityChartData.value,
}]);
const {
  result: storageDistribution,
  querying: distributionLoading,
  query: queryStorageDistribution,
} = useQuery(() => aggregateApi.fetchAggregateTrees({
  storage_cluster_id: clusterId.value,
}), { data: [] });

async function loadCapacity(force = false) {
  if (!clusterId.value || (loaded.capacity && !force)) return;
  loading.capacity = true;
  try {
    capacity.value = await storageClusterApi.fetchCapacityChange(clusterId.value, queryParams());
    loaded.capacity = true;
  } catch {
    capacity.value = { data: [] };
    ElMessage.error('加载容量趋势失败，请稍后重试');
  } finally {
    loading.capacity = false;
  }
}

async function loadDistribution(force = false) {
  if (!clusterId.value || (loaded.distribution && !force)) return;
  try {
    await queryStorageDistribution();
    loaded.distribution = true;
  } catch {
    storageDistribution.value = { data: [] };
    ElMessage.error('加载存储分布失败，请稍后重试');
  }
}

async function loadPerformance(force = false) {
  if (!clusterId.value || (loaded.performance && !force)) return;
  loading.performance = true;
  try {
    latency.value = await storageClusterApi.fetchTopLatency(clusterId.value, {
      ...queryParams(),
      object_type: 'volume',
      limit: performanceLimit.value,
    });
    loaded.performance = true;
  } catch {
    latency.value = { supported: true, data: [] };
    ElMessage.error('加载性能数据失败，请稍后重试');
  } finally {
    loading.performance = false;
  }
}

async function loadFaults(force = false) {
  if (!clusterId.value || (loaded.faults && !force)) return;
  loading.faults = true;
  try {
    const [severityResponse, faultResponse, eventResponse] = await Promise.all([
      storageClusterApi.fetchErrorSeverity(clusterId.value, queryParams()),
      storageClusterApi.fetchRepeatedFaults(clusterId.value, queryParams()),
      storageClusterApi.fetchSystemEvents(clusterId.value, systemEventQueryParams()),
    ]);
    severity.value = severityResponse;
    faults.value = faultResponse;
    applySystemEventResponse(eventResponse);
    loaded.faults = true;
  } catch {
    severity.value = { counts: {}, total: 0, sources: {} };
    faults.value = { data: [] };
    systemEvents.value = { data: [] };
    systemEventPagination.total = 0;
    ElMessage.error('加载故障数据失败，请稍后重试');
  } finally {
    loading.faults = false;
  }
}

function applySystemEventResponse(response) {
  systemEvents.value = response || { data: [] };
  systemEventPagination.total = Number(response?.total) || 0;
  systemEventPagination.page = Number(response?.page) || systemEventPagination.page;
  systemEventPagination.pageSize = Number(response?.page_size) || systemEventPagination.pageSize;
}

async function loadSystemEvents(resetPage = false) {
  if (!clusterId.value) return;
  if (resetPage) systemEventPagination.page = 1;
  loading.systemEvents = true;
  try {
    applySystemEventResponse(
      await storageClusterApi.fetchSystemEvents(clusterId.value, systemEventQueryParams()),
    );
  } catch {
    systemEvents.value = { data: [] };
    systemEventPagination.total = 0;
    ElMessage.error('加载系统事件失败，请稍后重试');
  } finally {
    loading.systemEvents = false;
  }
}

async function openSystemEventDetail(row) {
  const eventId = row?.sample_event_id || row?.id;
  if (!clusterId.value || !eventId) return;
  loading.systemEventDetail = true;
  systemEventDetailVisible.value = true;
  systemEventDetail.value = null;
  try {
    systemEventDetail.value = await storageClusterApi.fetchSystemEventDetail(
      clusterId.value,
      eventId,
    );
  } catch {
    systemEventDetailVisible.value = false;
    ElMessage.error('加载厂商事件日志失败，请稍后重试');
  } finally {
    loading.systemEventDetail = false;
  }
}

function resetSystemEventFilters() {
  systemEventFilters.keyword = '';
  systemEventFilters.severity = '';
  loadSystemEvents(true);
}

function changeSystemEventPage(page) {
  systemEventPagination.page = page;
  loadSystemEvents();
}

function changeSystemEventPageSize(pageSize) {
  systemEventPagination.pageSize = pageSize;
  loadSystemEvents(true);
}

function loadActiveTab(force = false) {
  if (activeTab.value === 'distribution') return loadDistribution(force);
  if (resourceTabNames.includes(activeTab.value)) return undefined;
  if (activeTab.value === 'performance') return loadPerformance(force);
  if (activeTab.value === 'faults') return loadFaults(force);
  if (activeTab.value === 'incidents') return undefined;
  return loadCapacity(force);
}

function searchActiveTab() {
  if (activeTab.value === 'faults') systemEventPagination.page = 1;
  return loadActiveTab(true);
}

function resetRange() {
  if (activeTab.value === 'performance') {
    performanceLimit.value = 10;
    selectedPerformanceObjects.value = [];
    selectedPerformanceMetrics.value = ['p95_latency'];
  }
  dateRange.value = getDefaultTime(8);
}

function exportFilename(response, format, section) {
  const headers = response?.headers;
  const disposition = headers?.['content-disposition'] || headers?.get?.('content-disposition') || '';
  const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
  if (match) {
    try {
      return decodeURIComponent(match[1] || match[2]).replace(/[\\/\r\n]/g, '_');
    } catch {
      return (match[1] || match[2]).replace(/[\\/\r\n]/g, '_');
    }
  }
  const extension = format === 'excel' ? 'xlsx' : format === 'csv' && section === 'all' ? 'zip' : format;
  return `storage-health-${clusterId.value}.${extension}`;
}

async function handleExport(command) {
  const [scope, format] = command.split(':');
  const sectionByTab = { capacity: 'capacity', performance: 'latency', faults: 'faults' };
  const section = scope === 'all' ? 'all' : scope === 'current' ? sectionByTab[activeTab.value] : scope;
  try {
    const response = await storageClusterApi.exportAnalytics(clusterId.value, {
      ...queryParams(),
      section,
      format,
    });
    const blob = response.data instanceof Blob ? response.data : new Blob([response.data]);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = exportFilename(response, format, section);
    document.body.appendChild(link);
    try {
      link.click();
    } finally {
      link.remove();
      URL.revokeObjectURL?.(url);
    }
  } catch {
    ElMessage.error('导出失败，请稍后重试');
  }
}

watch(activeTab, () => loadActiveTab());
watch(dateRange, () => {
  systemEventPagination.page = 1;
  loaded.capacity = false;
  loaded.performance = false;
  loaded.faults = false;
  loadActiveTab(true);
});

watch(clusterId, () => {
  loaded.capacity = false;
  loaded.distribution = false;
  loaded.performance = false;
  loaded.faults = false;
  queryInfo();
  loadActiveTab(true);
});

watch(performanceObjectOptions, (options) => {
  const availableValues = new Set(options.map((option) => option.value));
  selectedPerformanceObjects.value = selectedPerformanceObjects.value.filter(
    (value) => availableValues.has(value),
  );
});

onBeforeMount(() => {
  const routeClusterId = Number.parseInt(route.params?.id, 10);
  if (Number.isInteger(routeClusterId)) clusterId.value = routeClusterId;
});
</script>

<template>
  <div class="storage-health-page flex flex-col flex-1 min-h-0">
    <ElCard
      v-if="clusterId"
      class="storage-health-page__card">
      <ElTabs
        v-model="activeTab"
        class="storage-health-page__tabs">
        <ElTabPane
          label="容量趋势"
          name="capacity">
          <FilterForm
            v-if="activeTab === 'capacity'"
            class="storage-health-filter"
            @query="searchActiveTab"
            @reset="resetRange">
            <ElFormItem
              label="时间范围"
              class="analytics-date-range query-form-field--date-range">
              <ElDatePicker
                v-model="dateRange"
                type="datetimerange"
                range-separator="至"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="YYYY-MM-DD HH:mm:ss"
                start-placeholder="开始日期时间"
                end-placeholder="结束日期时间"
                :shortcuts="shortcuts" />
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
            v-if="loading.capacity"
            width="100%"
            height="520px" />
          <div
            v-else-if="!capacityData.length"
            class="analytics-empty">暂无容量数据</div>
          <div v-else>
            <ElDescriptions
              :column="4"
              border>
              <ElDescriptionsItem label="期初已使用">{{ capacityLabel('start_used') }}</ElDescriptionsItem>
              <ElDescriptionsItem label="期末已使用">{{ capacityLabel('end_used') }}</ElDescriptionsItem>
              <ElDescriptionsItem label="变化量">{{ capacityLabel('change') }}</ElDescriptionsItem>
              <ElDescriptionsItem label="变化率">{{ capacity.change_percent == null ? '-' : `${capacity.change_percent}%` }}</ElDescriptionsItem>
            </ElDescriptions>
            <StorageTrendChart
              :series="capacitySeries"
              indicator="used"
              :trend-meta="capacity.trend_meta"
              aria-label="存储集群已使用容量趋势"
              height="520px"
              :unit="capacityUnit" />
          </div>
        </ElTabPane>

        <ElTabPane
          label="存储分布"
          name="distribution">
          <div
            v-loading="distributionLoading"
            class="analytics-chart-stage"
            :aria-busy="distributionLoading">
            <div
              v-if="!distributionLoading && !storageDistribution.data?.length"
              class="analytics-empty">暂无存储分布数据</div>
            <DiskUsage
              v-else-if="storageDistribution.data?.length"
              :data="storageDistribution.data"
              title=""
              width="100%"
              height="100%" />
          </div>
        </ElTabPane>

        <ElTabPane
          label="容量池"
          name="aggregates">
          <ClusterResourceListTab
            v-if="activeTab === 'aggregates' && clusterId"
            :cluster-id="clusterId"
            resource-type="aggregate" />
        </ElTabPane>

        <ElTabPane
          label="存储空间"
          name="volumes">
          <ClusterResourceListTab
            v-if="activeTab === 'volumes' && clusterId"
            :cluster-id="clusterId"
            resource-type="volume" />
        </ElTabPane>

        <ElTabPane
          v-if="infoResult?.storage_type && infoResult?.storage_type !== 'isilon'"
          label="Qtree（NetApp）"
          name="qtrees">
          <ClusterResourceListTab
            v-if="activeTab === 'qtrees' && clusterId"
            :cluster-id="clusterId"
            resource-type="qtree" />
        </ElTabPane>

        <ElTabPane
          label="性能分析"
          name="performance">
          <FilterForm
            v-if="activeTab === 'performance'"
            class="storage-health-filter"
            @query="searchActiveTab"
            @reset="resetRange">
            <ElFormItem
              label="时间范围"
              class="analytics-date-range query-form-field--date-range">
              <ElDatePicker
                v-model="dateRange"
                type="datetimerange"
                range-separator="至"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="YYYY-MM-DD HH:mm:ss"
                start-placeholder="开始日期时间"
                end-placeholder="结束日期时间"
                :shortcuts="shortcuts" />
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
            v-if="loading.performance"
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
            <div class="table-wrap">
              <ElTable :data="filteredLatencyData">
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
              </ElTable>
            </div>
          </div>
        </ElTabPane>

        <ElTabPane
          label="故障分析"
          name="faults">
          <FilterForm
            v-if="activeTab === 'faults'"
            class="storage-health-filter"
            @query="searchActiveTab"
            @reset="resetRange">
            <ElFormItem
              label="时间范围"
              class="analytics-date-range query-form-field--date-range">
              <ElDatePicker
                v-model="dateRange"
                type="datetimerange"
                range-separator="至"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="YYYY-MM-DD HH:mm:ss"
                start-placeholder="开始日期时间"
                end-placeholder="结束日期时间"
                :shortcuts="shortcuts" />
            </ElFormItem>
            <template #actions>
              <ElDropdown @command="handleExport">
                <ElButton type="primary">导出报告</ElButton>
                <template #dropdown>
                  <ElDropdownMenu>
                    <ElDropdownItem command="severity:csv">错误级别 CSV</ElDropdownItem>
                    <ElDropdownItem command="severity:excel">错误级别 Excel</ElDropdownItem>
                    <ElDropdownItem command="severity:pdf">错误级别 PDF</ElDropdownItem>
                    <ElDropdownItem command="faults:csv">重复故障 CSV</ElDropdownItem>
                    <ElDropdownItem command="faults:excel">重复故障 Excel</ElDropdownItem>
                    <ElDropdownItem command="faults:pdf">重复故障 PDF</ElDropdownItem>
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
            v-if="loading.faults"
            width="100%"
            height="360px" />
          <div v-else>
            <div
              v-if="!severity.total && !faultData.length"
              class="fault-analysis-empty">当前时间范围内暂无故障数据；如设备已有告警，请检查厂商事件采集权限</div>
            <div
              v-else
              class="fault-grid">
              <PieCharts
                :data="severityChartData"
                title="错误严重级别"
                width="100%"
                height="360px" />
              <div class="table-wrap">
                <ElTable
                  :data="faultData"
                  empty-text="暂无重复故障">
                  <ElTableColumn
                    label="来源"
                    class-name="mobile-hidden tablet-hidden"
                    label-class-name="mobile-hidden tablet-hidden"
                    prop="source" />
                  <ElTableColumn
                    label="事件代码与含义"
                    min-width="260"
                    show-overflow-tooltip>
                    <template #default="{ row }">
                      <strong>{{ row.title_zh || '未收录的厂商事件代码' }}</strong>
                      <div class="repeated-event__code">{{ row.event_code || '-' }}</div>
                    </template>
                  </ElTableColumn>
                  <ElTableColumn
                    label="关联类型"
                    min-width="130">
                    <template #default="{ row }">
                      <ElTag :type="row.association_type === 'fault_log' ? 'danger' : 'warning'">
                        {{ row.association_type_label || '未分类厂商事件' }}
                      </ElTag>
                    </template>
                  </ElTableColumn>
                  <ElTableColumn
                    label="日志摘要"
                    class-name="mobile-hidden tablet-hidden"
                    label-class-name="mobile-hidden tablet-hidden"
                    prop="log_excerpt"
                    min-width="260"
                    show-overflow-tooltip />
                  <ElTableColumn
                    label="次数"
                    prop="count" />
                  <ElTableColumn
                    label="首次发生"
                    class-name="mobile-hidden tablet-hidden"
                    label-class-name="mobile-hidden tablet-hidden"
                    prop="first_occurred_at" />
                  <ElTableColumn
                    label="最近发生"
                    prop="last_occurred_at" />
                  <ElTableColumn
                    label="操作"
                    align="right"
                    fixed="right"
                    width="110">
                    <template #default="{ row }">
                      <div class="list-row-actions">
                        <TableActionButton
                          :data-testid="`repeated-event-log-${row.sample_event_id}`"
                          action="detail"
                          @click="openSystemEventDetail(row)">查看日志</TableActionButton>
                      </div>
                    </template>
                  </ElTableColumn>
                </ElTable>
              </div>
            </div>
            <div class="system-events">
              <div class="system-events__heading">
                <h3>系统事件</h3>
              </div>
              <FilterForm
                class="system-event-filter"
                @query="loadSystemEvents(true)"
                @reset="resetSystemEventFilters">
                <ElFormItem label="关键字">
                  <ElInput
                    v-model="systemEventFilters.keyword"
                    clearable
                    placeholder="事件代码、对象或内容" />
                </ElFormItem>
                <ElFormItem label="日志等级">
                  <ElSelect
                    v-model="systemEventFilters.severity"
                    clearable
                    placeholder="全部等级">
                    <ElOption
                      label="严重"
                      value="critical" />
                    <ElOption
                      label="错误"
                      value="error" />
                    <ElOption
                      label="警告"
                      value="warning" />
                    <ElOption
                      label="信息"
                      value="info" />
                  </ElSelect>
                </ElFormItem>
              </FilterForm>
              <ElTable
                v-loading="loading.systemEvents"
                :data="systemEventData"
                empty-text="暂无系统事件">
                <ElTableColumn
                  label="来源"
                  class-name="mobile-hidden tablet-hidden"
                  label-class-name="mobile-hidden tablet-hidden"
                  prop="source" />
                <ElTableColumn
                  label="级别"
                  prop="severity" />
                <ElTableColumn
                  label="事件代码与含义"
                  min-width="250"
                  show-overflow-tooltip>
                  <template #default="{ row }">
                    <strong>{{ vendorEventTitle(row) }}</strong>
                    <div class="repeated-event__code">{{ row.event_code || '-' }}</div>
                  </template>
                </ElTableColumn>
                <ElTableColumn
                  label="关联类型"
                  min-width="120">
                  <template #default="{ row }">
                    <ElTooltip
                      placement="top"
                      effect="light"
                      popper-class="system-event-association-tooltip">
                      <template #content>
                        <div class="system-event-association-guidance">
                          <strong>关联提示</strong>
                          <p>{{ vendorEventDescription(row) }}</p>
                          <strong>采取措施</strong>
                          <p>{{ vendorEventRecommendedSolution(row) }}</p>
                        </div>
                      </template>
                      <ElTag :type="vendorEventAssociationTagType(row)">
                        {{ vendorEventAssociationLabel(row) }}
                      </ElTag>
                    </ElTooltip>
                  </template>
                </ElTableColumn>
                <ElTableColumn
                  label="事件对象"
                  class-name="mobile-hidden tablet-hidden"
                  label-class-name="mobile-hidden tablet-hidden"
                  prop="object_name">
                  <template #default="{ row }">
                    <span :title="row.object_id && row.object_id !== row.object_name ? `原始标识：${row.object_id}` : undefined">
                      {{ row.object_name || row.object_id || '-' }}
                    </span>
                  </template>
                </ElTableColumn>
                <ElTableColumn
                  label="内容"
                  class-name="mobile-hidden tablet-hidden"
                  label-class-name="mobile-hidden tablet-hidden"
                  prop="description"
                  show-overflow-tooltip />
                <ElTableColumn
                  label="发生时间"
                  prop="occurred_at" />
                <ElTableColumn
                  label="操作"
                  align="right"
                  fixed="right"
                  width="110">
                  <template #default="{ row }">
                    <div class="list-row-actions">
                      <TableActionButton
                        action="detail"
                        @click="openSystemEventDetail(row)">查看日志</TableActionButton>
                    </div>
                  </template>
                </ElTableColumn>
              </ElTable>
              <ElPagination
                v-if="systemEventPagination.total > 0"
                class="system-event-pagination"
                background
                layout="total, sizes, prev, pager, next, jumper"
                :current-page="systemEventPagination.page"
                :page-size="systemEventPagination.pageSize"
                :page-sizes="[20, 50, 100]"
                :total="systemEventPagination.total"
                @current-change="changeSystemEventPage"
                @size-change="changeSystemEventPageSize" />
            </div>
          </div>
        </ElTabPane>
        <ElTabPane
          label="耗尽风险"
          name="exhaustion-risk"
          lazy>
          <CapacityExhaustionRiskPanel
            asset-type="storage_cluster"
            :asset-id="clusterId" />
        </ElTabPane>
        <ElTabPane
          label="关联事件"
          name="incidents">
          <ClusterIncidentsTab
            v-if="activeTab === 'incidents' && clusterId"
            :cluster-id="clusterId" />
        </ElTabPane>
      </ElTabs>
    </ElCard>
    <ElDialog
      v-model="systemEventDetailVisible"
      title="事件日志详情"
      width="min(720px, 96vw)">
      <div
        v-loading="loading.systemEventDetail"
        class="system-event-detail">
        <ElDescriptions
          v-if="systemEventDetail"
          :column="2"
          border>
          <ElDescriptionsItem label="存储类型">{{ systemEventDetail.source || '-' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="关联类型">{{ vendorEventAssociationLabel(systemEventDetail) }}</ElDescriptionsItem>
          <ElDescriptionsItem label="事件代码">{{ systemEventDetail.event_code || '-' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="审核状态">{{ vendorEventReviewLabel(systemEventDetail) }}</ElDescriptionsItem>
          <ElDescriptionsItem label="中文含义">{{ vendorEventTitle(systemEventDetail) }}</ElDescriptionsItem>
          <ElDescriptionsItem label="事件对象">{{ systemEventDetail.object_name || systemEventDetail.object_id || '集群' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="发生时间">{{ systemEventDetail.occurred_at || '-' }}</ElDescriptionsItem>
          <ElDescriptionsItem
            label="规范化日志"
            :span="2"><pre>{{ systemEventDetail.description || '-' }}</pre></ElDescriptionsItem>
          <ElDescriptionsItem
            label="中文说明"
            :span="2">{{ vendorEventDescription(systemEventDetail) }}</ElDescriptionsItem>
          <ElDescriptionsItem
            label="推荐解决方案"
            :span="2">{{ vendorEventRecommendedSolution(systemEventDetail) }}</ElDescriptionsItem>
        </ElDescriptions>
        <details v-if="systemEventDetail?.fingerprint">
          <summary>技术关联信息</summary>
          <code>{{ systemEventDetail.fingerprint }}</code>
        </details>
      </div>
    </ElDialog>
  </div>
</template>

<style lang="scss" scoped>
/* Hallmark · pre-emit critique: P5 H5 E5 S5 R5 V4 · genre: modern-minimal · macrostructure: Workbench · tone: technical · anchor hue: existing blue */
.storage-health-page {
  overflow-x: hidden;
}

.storage-health-page__card {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}
.repeated-event__code { margin-top: 2px; color: var(--text-secondary); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: var(--font-size-xs); }
.system-event-association-guidance { max-width: 360px; line-height: 1.5; }
.system-event-association-guidance p { margin: var(--spacing-xs) 0 var(--spacing-sm); }
.system-event-association-guidance p:last-child { margin-bottom: 0; }
.system-event-detail { display: grid; gap: var(--spacing-sm); min-height: 120px; }
.system-event-detail pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: var(--font-size-sm); }
.system-event-detail details { color: var(--text-secondary); }
.system-event-detail code { display: block; margin-top: var(--spacing-xs); overflow-wrap: anywhere; }

.storage-health-page__card :deep(.el-card__body) {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.storage-health-page__tabs {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.storage-health-page__tabs :deep(.el-tabs__header) {
  flex: 0 0 auto;
}

.storage-health-page__tabs :deep(.el-tabs__content) {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

.storage-health-page__tabs :deep(.el-tab-pane) {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  min-width: 0;
  width: 100%;
}

.storage-health-filter {
  margin-bottom: var(--spacing-md);
}

:deep(.analytics-date-range .el-date-editor) {
  width: 100%;
}

.analytics-chart-stage {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
  position: relative;
}

.analytics-empty {
  display: grid;
  min-height: 360px;
  place-items: center;
  color: var(--el-text-color-secondary);
}

.fault-grid {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(0, 2fr);
  gap: 16px;
}

.table-wrap {
  max-width: 100%;
  overflow-x: hidden;
  overflow-y: auto;
}

.storage-health-page :deep(.el-table__body-wrapper) {
  overflow-x: hidden !important;
}

.storage-health-page :deep(.el-table .cell) {
  overflow-wrap: anywhere;
  white-space: normal;
}

.performance-charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 480px), 1fr));
  gap: var(--spacing-md);
}

.fault-analysis-empty {
  padding: var(--spacing-xl) 0;
  color: var(--el-text-color-secondary);
  text-align: center;
}

.system-events {
  margin-top: 20px;
}

.system-events__heading {
  margin-bottom: var(--spacing-md);

  p {
    margin-top: var(--spacing-xs);
    color: var(--text-tertiary);
    font-size: var(--font-size-sm);
  }
}

.system-event-filter {
  margin-bottom: var(--spacing-md);
}

.system-event-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-md);
}

@media (max-width: 960px) {
  .fault-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
