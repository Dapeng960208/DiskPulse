<script setup>
import {
  ElButton,
  ElCard,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElFormItem,
  ElMessage,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
} from 'element-plus';
import { computed, onBeforeMount, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import FilterForm from '@/components/form/QueryForm.vue';
import LineCharts from '@/common/charts/LineCharts.vue';
import PieCharts from '@/common/charts/PieCharts.vue';
import BarStackChart from '@/common/charts/BarStackChart.vue';
import DiskUsage from '@/common/charts/DiskUsage.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import aggregateApi from '@/api/aggregate-api.js';
import storageClusterApi from '@/api/storage-cluster-api';
import { useQuery } from '@/composables/query';
import { getDefaultTime } from '@/composables/common';

const route = useRoute();
const clusterId = ref(null);
const dateRange = ref(getDefaultTime(8));
const activeTab = ref('capacity');
const capacity = ref({ data: [] });
const latency = ref({ supported: true, data: [] });
const severity = ref({ counts: {}, total: 0, sources: {} });
const faults = ref({ data: [] });
const systemEvents = ref({ data: [] });
const loaded = reactive({ capacity: false, distribution: false, performance: false, faults: false });
const loading = reactive({ capacity: false, performance: false, faults: false });

const shortcuts = [
  { text: '一天内', value: () => getDefaultTime(8) },
  { text: '一周内', value: () => getDefaultTime(24 * 7) },
  { text: '一月内', value: () => getDefaultTime(24 * 30) },
  { text: '三月内', value: () => getDefaultTime(24 * 90) },
];

const queryParams = () => ({
  start_time: dateRange.value?.[0],
  end_time: dateRange.value?.[1],
});

const capacityData = computed(() => capacity.value?.data || []);
const capacityChartData = computed(() => capacityData.value.map((item) => [item.updated_at, Number(item.used)]));
const latencyData = computed(() => latency.value?.data || []);
const latencyCategories = computed(() => latencyData.value.map((item) => item.object_name || item.object_id || '-'));
const latencySeries = computed(() => [latencyData.value.map((item) => Number(item.p95_latency) || 0)]);
const faultData = computed(() => faults.value?.data || []);
const systemEventData = computed(() => systemEvents.value?.data || []);
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
    latency.value = await storageClusterApi.fetchTopLatency(clusterId.value, queryParams());
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
    [severity.value, faults.value, systemEvents.value] = await Promise.all([
      storageClusterApi.fetchErrorSeverity(clusterId.value, queryParams()),
      storageClusterApi.fetchRepeatedFaults(clusterId.value, queryParams()),
      storageClusterApi.fetchSystemEvents(clusterId.value, queryParams()),
    ]);
    loaded.faults = true;
  } catch {
    severity.value = { counts: {}, total: 0, sources: {} };
    faults.value = { data: [] };
    systemEvents.value = { data: [] };
    ElMessage.error('加载故障数据失败，请稍后重试');
  } finally {
    loading.faults = false;
  }
}

function loadActiveTab(force = false) {
  if (activeTab.value === 'distribution') return loadDistribution(force);
  if (activeTab.value === 'performance') return loadPerformance(force);
  if (activeTab.value === 'faults') return loadFaults(force);
  return loadCapacity(force);
}

function resetRange() {
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

onBeforeMount(() => {
  const routeClusterId = Number.parseInt(route.params?.id, 10);
  if (Number.isInteger(routeClusterId)) clusterId.value = routeClusterId;
});
</script>

<template>
  <div class="storage-health-page flex flex-col flex-1 min-h-0">
    <ElCard
      v-if="clusterId"
      class="mt-2.5 flex-auto min-h-0">
      <ElTabs
        v-model="activeTab"
        class="h-full">
        <FilterForm
          v-if="activeTab !== 'distribution'"
          class="storage-health-filter"
          @query="loadActiveTab(true)"
          @reset="resetRange">
          <ElFormItem
            label="时间范围"
            class="analytics-date-range query-form-field--wide">
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
                  <template v-if="activeTab === 'capacity' || activeTab === 'performance'">
                    <ElDropdownItem command="current:csv">当前页 CSV</ElDropdownItem>
                    <ElDropdownItem command="current:excel">当前页 Excel</ElDropdownItem>
                    <ElDropdownItem command="current:pdf">当前页 PDF</ElDropdownItem>
                  </template>
                  <template v-else-if="activeTab === 'faults'">
                    <ElDropdownItem command="severity:csv">错误级别 CSV</ElDropdownItem>
                    <ElDropdownItem command="severity:excel">错误级别 Excel</ElDropdownItem>
                    <ElDropdownItem command="severity:pdf">错误级别 PDF</ElDropdownItem>
                    <ElDropdownItem command="faults:csv">重复故障 CSV</ElDropdownItem>
                    <ElDropdownItem command="faults:excel">重复故障 Excel</ElDropdownItem>
                    <ElDropdownItem command="faults:pdf">重复故障 PDF</ElDropdownItem>
                  </template>
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

        <ElTabPane
          label="容量趋势"
          name="capacity">
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
              <ElDescriptionsItem label="期初已使用">{{ capacity.start_used ?? '-' }}</ElDescriptionsItem>
              <ElDescriptionsItem label="期末已使用">{{ capacity.end_used ?? '-' }}</ElDescriptionsItem>
              <ElDescriptionsItem label="变化量">{{ capacity.change ?? '-' }}</ElDescriptionsItem>
              <ElDescriptionsItem label="变化率">{{ capacity.change_percent == null ? '-' : `${capacity.change_percent}%` }}</ElDescriptionsItem>
            </ElDescriptions>
            <LineCharts
              :data="capacityChartData"
              title="已使用容量变化"
              width="100%"
              height="520px"
              :show-stats="true"
              y-axis-unit="G"
              :legend-name="infoResult.name" />
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
              height="520px" />
          </div>
        </ElTabPane>

        <ElTabPane
          label="性能分析"
          name="performance">
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
            <BarStackChart
              :data="latencySeries"
              :categories="latencyCategories"
              :series-names="['p95']"
              :series-map="{ p95: 'P95 延迟' }"
              title="Top 10 高延迟对象"
              unit="ms"
              width="100%"
              height="360px" />
            <div class="table-wrap">
              <ElTable :data="latencyData">
                <ElTableColumn
                  label="对象"
                  prop="object_name"
                  min-width="160" />
                <ElTableColumn
                  label="类型"
                  prop="object_type" />
                <ElTableColumn
                  label="P95 延迟(ms)"
                  prop="p95_latency" />
                <ElTableColumn
                  label="平均延迟(ms)"
                  prop="avg_latency" />
                <ElTableColumn
                  label="最大延迟(ms)"
                  prop="max_latency" />
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
          <LoadingCharts
            v-if="loading.faults"
            width="100%"
            height="360px" />
          <div
            v-else-if="!severity.total && !faultData.length && !systemEventData.length"
            class="analytics-empty">当前时间范围内暂无故障数据；如设备已有告警，请检查厂商事件采集权限</div>
          <div v-else>
            <div class="fault-grid">
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
                    prop="source" />
                  <ElTableColumn
                    label="故障指纹"
                    prop="fingerprint"
                    min-width="220" />
                  <ElTableColumn
                    label="次数"
                    prop="count" />
                  <ElTableColumn
                    label="首次发生"
                    prop="first_occurred_at"
                    min-width="170" />
                  <ElTableColumn
                    label="最近发生"
                    prop="last_occurred_at"
                    min-width="170" />
                </ElTable>
              </div>
            </div>
            <div class="system-events">
              <h3>系统事件</h3>
              <ElTable
                :data="systemEventData"
                empty-text="暂无系统事件">
                <ElTableColumn
                  label="来源"
                  prop="source" />
                <ElTableColumn
                  label="级别"
                  prop="severity" />
                <ElTableColumn
                  label="事件代码"
                  prop="event_code"
                  min-width="180" />
                <ElTableColumn
                  label="对象"
                  prop="object_id"
                  min-width="140" />
                <ElTableColumn
                  label="内容"
                  prop="description"
                  min-width="320" />
                <ElTableColumn
                  label="发生时间"
                  prop="occurred_at"
                  min-width="170" />
              </ElTable>
            </div>
          </div>
        </ElTabPane>
      </ElTabs>
    </ElCard>
  </div>
</template>

<style lang="scss" scoped>
/* Hallmark · pre-emit critique: P5 H5 E5 S5 R5 V4 · genre: modern-minimal · macrostructure: Workbench · tone: technical · anchor hue: existing blue */
.storage-health-page {
  overflow-x: hidden;
}

.storage-health-filter {
  margin-bottom: var(--spacing-md);
}

:deep(.analytics-date-range.query-form-field--wide) {
  flex-basis: 480px;
  width: 480px;
  min-width: 0;
  max-width: 100%;
}

:deep(.analytics-date-range .el-date-editor) {
  width: 100%;
}

.analytics-chart-stage {
  min-height: 520px;
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
  overflow-x: auto;
}

.system-events {
  margin-top: 20px;
}

:deep(.el-card__body) {
  height: 100%;
}

@media (max-width: 960px) {
  .fault-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
