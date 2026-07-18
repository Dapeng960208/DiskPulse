<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { ElEmpty, ElMessage, ElSkeleton } from 'element-plus';
import dashboardApi from '@/api/dashboard-api.js';
import PieCharts from '@/common/charts/PieCharts.vue';
import DashboardChart from '@/components/dashboard/DashboardChart.vue';
import StorageTrendChart from '@/components/dashboard/StorageTrendChart.vue';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import { getCssColor } from '@/lib/echarts.js';
import { hasRole } from '@/utils/authorization';

const projectId = ref(null);
const summaryResponse = ref(null);
const capacityTrend = ref([]);
const capacityItems = ref([]);
const alertLevels = ref([]);
const topUsers = ref([]);
const loading = reactive({ summary: true, trend: true, items: true, alerts: true, users: false });
let requestId = 0;

const token = (name, fallback) => getCssColor(name, fallback);
const primary = () => token('--primary-color', '#3B82F6');
const primaryLight = () => token('--primary-lighter', '#93C5FD');
const warning = () => token('--warning-color', '#F59E0B');
const dangerLight = () => token('--danger-light', '#F87171');
const danger = () => token('--danger-color', '#EF4444');
const background = () => token('--bg-primary', '#FFFFFF');
const gridColor = () => token('--border-light', '#F1F5F9');
const axisColor = () => token('--text-tertiary', '#94A3B8');

const isProject = computed(() => Boolean(projectId.value));
const canViewGlobalDashboard = computed(() => hasRole('superadmin'));
const needsProjectSelection = computed(() => !canViewGlobalDashboard.value && !isProject.value);
const scope = computed(() => summaryResponse.value?.scope || {});
const summary = computed(() => summaryResponse.value?.summary || {});
const limitLabel = computed(() => (isProject.value ? '项目限额' : '物理总容量'));
const comparisonTitle = computed(() => (isProject.value ? '项目组容量对比' : '项目容量对比'));
const pieData = computed(() => [
  { name: '已使用', value: Number(summary.value.used_gb) || 0 },
  { name: '可使用', value: Number(summary.value.available_gb) || 0 },
]);

function formatCapacity(value) {
  const number = Number(value) || 0;
  if (number >= 1024 * 1024) return `${(number / 1024 / 1024).toFixed(2)} PB`;
  if (number >= 1024) return `${(number / 1024).toFixed(2)} TB`;
  return `${number.toFixed(2)} GB`;
}

const trendSeries = computed(() => [{
  name: '已使用',
  data: capacityTrend.value.map((item) => [item.timestamp, item.used_gb]),
}]);

const comparisonOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (value) => formatCapacity(value) },
  legend: { bottom: 0, textStyle: { color: axisColor() } },
  grid: { left: 8, right: 20, top: 12, bottom: 36, containLabel: true },
  xAxis: {
    type: 'value',
    axisLabel: { color: axisColor(), formatter: (value) => formatCapacity(value) },
    splitLine: { lineStyle: { color: gridColor(), type: 'dashed' } },
  },
  yAxis: {
    type: 'category',
    inverse: true,
    data: capacityItems.value.map((item) => item.name),
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: axisColor(), width: 100, overflow: 'truncate' },
  },
  series: [
    { name: '已使用', type: 'bar', stack: 'capacity', barWidth: 14, itemStyle: { color: primary(), borderRadius: [4, 0, 0, 4] }, data: capacityItems.value.map((item) => item.used_gb) },
    { name: '可使用', type: 'bar', stack: 'capacity', barWidth: 14, itemStyle: { color: primaryLight(), borderRadius: [0, 4, 4, 0] }, data: capacityItems.value.map((item) => item.available_gb) },
  ],
}));

const topUsersOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (value) => formatCapacity(value) },
  grid: { left: 8, right: 28, top: 12, bottom: 12, containLabel: true },
  xAxis: {
    type: 'value',
    axisLabel: { color: axisColor(), formatter: (value) => formatCapacity(value) },
    splitLine: { lineStyle: { color: gridColor(), type: 'dashed' } },
  },
  yAxis: {
    type: 'category',
    inverse: true,
    data: topUsers.value.map((item) => item.name),
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: axisColor(), width: 100, overflow: 'truncate' },
  },
  series: [{
    name: '已使用',
    type: 'bar',
    barWidth: 14,
    itemStyle: { color: primary(), borderRadius: [0, 4, 4, 0] },
    label: { show: true, position: 'right', color: axisColor(), formatter: ({ value }) => formatCapacity(value) },
    data: topUsers.value.map((item) => item.used_gb),
  }],
}));

const alertOption = computed(() => ({
  color: [warning(), dangerLight(), danger()],
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: axisColor() } },
  series: [{
    name: '告警级别',
    type: 'pie',
    radius: '68%',
    center: ['50%', '44%'],
    itemStyle: { borderColor: background(), borderWidth: 2, borderRadius: 4 },
    label: { color: axisColor(), formatter: '{b}\n{c}' },
    data: alertLevels.value.map((item) => ({ name: item.name, value: item.count })),
  }],
}));

async function loadDashboard() {
  const currentRequest = ++requestId;
  if (needsProjectSelection.value) {
    // Review fix: project members must not issue dashboard requests without project scope.
    summaryResponse.value = null;
    capacityTrend.value = [];
    capacityItems.value = [];
    alertLevels.value = [];
    topUsers.value = [];
    Object.assign(loading, { summary: false, trend: false, items: false, alerts: false, users: false });
    return;
  }
  const params = projectId.value ? { project_id: projectId.value } : {};
  summaryResponse.value = null;
  capacityTrend.value = [];
  capacityItems.value = [];
  alertLevels.value = [];
  topUsers.value = [];
  Object.assign(loading, {
    summary: true,
    trend: true,
    items: true,
    alerts: true,
    users: isProject.value,
  });

  const requests = [
    ['summary', dashboardApi.fetchSummary(params), (value) => (summaryResponse.value = value)],
    ['trend', dashboardApi.fetchCapacityTrend(params), (value) => (capacityTrend.value = value)],
    ['items', dashboardApi.fetchCapacityItems(params), (value) => (capacityItems.value = value)],
    ['alerts', dashboardApi.fetchAlertLevels(params), (value) => (alertLevels.value = value)],
  ];
  if (isProject.value) {
    requests.push(['users', dashboardApi.fetchTopUsers(params), (value) => (topUsers.value = value)]);
  }

  let failed = false;
  await Promise.allSettled(requests.map(async ([key, request, apply]) => {
    try {
      const value = await request;
      if (currentRequest === requestId) apply(value);
    } catch {
      failed = true;
    } finally {
      if (currentRequest === requestId) loading[key] = false;
    }
  }));
  if (currentRequest === requestId && failed) {
    ElMessage.error('加载存储概览失败，请稍后重试');
  }
}

watch(projectId, loadDashboard);
onMounted(loadDashboard);
</script>

<template>
  <main class="dashboard-page">
    <header class="dashboard-header">
      <div>
        <h1>存储概览</h1>
        <p>{{ isProject ? (scope.project_name || '项目数据加载中') : '全局存储运行视图' }}</p>
      </div>
      <div class="dashboard-controls">
        <ProjectSelect
          v-model="projectId"
          class="project-filter"
          clearable
          placeholder="全部项目" />
        <span class="period-chip">近 30 天</span>
      </div>
    </header>

    <section
      class="summary-strip"
      aria-label="容量摘要">
      <template v-if="loading.summary">
        <div
          v-for="index in 4"
          :key="index"
          class="summary-item summary-item-loading">
          <ElSkeleton
            :rows="1"
            animated />
        </div>
      </template>
      <template v-else-if="summaryResponse">
        <div class="summary-item">
          <span>{{ limitLabel }}</span>
          <strong>{{ formatCapacity(summary.limit_gb) }}</strong>
        </div>
        <div class="summary-item">
          <span>已使用</span>
          <strong>{{ formatCapacity(summary.used_gb) }}</strong>
        </div>
        <div class="summary-item">
          <span>可使用</span>
          <strong>{{ formatCapacity(summary.available_gb) }}</strong>
        </div>
        <div class="summary-item summary-alert">
          <span>近 30 天告警</span>
          <strong>{{ summary.alert_count }}</strong>
        </div>
      </template>
      <ElEmpty
        v-else
        class="summary-empty"
        :description="needsProjectSelection ? '请选择项目以查看存储概览' : '暂无摘要数据'" />
    </section>

    <section class="dashboard-grid dashboard-grid-main">
      <article class="dashboard-panel trend-panel">
        <div class="panel-heading">
          <h2>容量趋势</h2>
          <span>已使用容量</span>
        </div>
        <ElSkeleton
          v-if="loading.trend"
          :rows="5"
          animated />
        <StorageTrendChart
          v-else-if="capacityTrend.length"
          :series="trendSeries"
          indicator="used"
          unit="G"
          :trend-meta="summaryResponse?.trend_meta"
          aria-label="近 30 天容量趋势"
          height="280px" />
        <ElEmpty
          v-else
          description="暂无容量趋势" />
      </article>

      <article class="dashboard-panel usage-panel">
        <div class="panel-heading">
          <h2>容量使用率</h2>
          <span>{{ summary.storage_cluster_count || 0 }} 个存储集群</span>
        </div>
        <ElSkeleton
          v-if="loading.summary"
          :rows="5"
          animated />
        <template v-else-if="summaryResponse">
          <PieCharts
            :data="pieData"
            title="容量使用率"
            variant="dashboard"
            :center-label="`${summary.use_ratio}%`"
            width="100%"
            height="230px" />
          <div class="usage-caption">
            <span><i class="used-dot"></i>已使用 {{ formatCapacity(summary.used_gb) }}</span>
            <span><i class="available-dot"></i>可使用 {{ formatCapacity(summary.available_gb) }}</span>
          </div>
        </template>
        <ElEmpty
          v-else
          description="暂无使用率数据" />
      </article>
    </section>

    <section
      class="dashboard-grid dashboard-grid-secondary"
      :style="{ '--dashboard-columns': isProject ? '2fr 2fr 1fr' : '1fr 1fr' }">
      <article class="dashboard-panel comparison-panel">
        <div class="panel-heading">
          <h2>{{ comparisonTitle }}</h2>
          <span>按已使用容量 Top 10</span>
        </div>
        <ElSkeleton
          v-if="loading.items"
          :rows="7"
          animated />
        <DashboardChart
          v-else-if="capacityItems.length"
          :option="comparisonOption"
          :aria-label="comparisonTitle"
          height="320px" />
        <ElEmpty
          v-else
          description="暂无容量对比数据" />
      </article>

      <article
        v-if="isProject"
        class="dashboard-panel top-users-panel">
        <div class="panel-heading">
          <h2>用户使用 Top 10</h2>
          <span>按用户目录已使用容量</span>
        </div>
        <ElSkeleton
          v-if="loading.users"
          :rows="7"
          animated />
        <DashboardChart
          v-else-if="topUsers.length"
          :option="topUsersOption"
          aria-label="项目内用户使用容量 Top 10"
          height="320px" />
        <ElEmpty
          v-else
          description="暂无用户使用数据" />
      </article>

      <article class="dashboard-panel alert-panel">
        <div class="panel-heading">
          <h2>告警级别</h2>
          <span>近 30 天</span>
        </div>
        <ElSkeleton
          v-if="loading.alerts"
          :rows="7"
          animated />
        <DashboardChart
          v-else-if="alertLevels.length"
          :option="alertOption"
          aria-label="近 30 天告警级别分布"
          height="320px" />
        <ElEmpty
          v-else
          description="暂无告警数据" />
      </article>
    </section>
  </main>
</template>

<style lang="scss" scoped>
.dashboard-page { display: grid; grid-auto-rows: max-content; align-content: start; gap: var(--spacing-xl); min-width: 0; background: var(--bg-secondary); }
.dashboard-header { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--spacing-xl); }
.dashboard-header h1 { margin: 0; color: var(--text-primary); font-size: var(--font-size-3xl); line-height: var(--line-height-tight); }
.dashboard-header p { margin: var(--spacing-xs) 0 0; color: var(--text-secondary); font-size: var(--font-size-sm); }
.dashboard-controls { display: flex; align-items: center; gap: var(--spacing-md); }
.project-filter { width: 240px; }
.period-chip { flex: none; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-primary); color: var(--text-secondary); font-size: var(--font-size-sm); }
.summary-strip { display: grid; grid-template-columns: repeat(4, 1fr); overflow: hidden; min-height: 84px; border: 1px solid var(--border-color); border-radius: var(--radius-lg); background: var(--bg-primary); box-shadow: var(--shadow-xs); }
.summary-item { display: grid; gap: var(--spacing-sm); padding: var(--spacing-xl) var(--spacing-2xl); border-right: 1px solid var(--border-light); }
.summary-item:last-child { border-right: 0; }
.summary-item span { color: var(--text-secondary); font-size: var(--font-size-sm); }
.summary-item strong { color: var(--text-primary); font-size: var(--font-size-2xl); line-height: 1; }
.summary-item-loading { align-content: center; }
.summary-alert strong { color: var(--warning-color); }
.summary-empty { grid-column: 1 / -1; }
.dashboard-grid { display: grid; gap: var(--spacing-xl); min-width: 0; }
.dashboard-grid-main { grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr); }
.dashboard-grid-secondary { grid-template-columns: var(--dashboard-columns); }
.dashboard-panel { min-width: 0; min-height: 380px; padding: var(--spacing-xl); border: 1px solid var(--border-color); border-radius: var(--radius-lg); background: var(--bg-primary); box-shadow: var(--shadow-xs); }
.trend-panel, .usage-panel { min-height: 330px; }
.panel-heading { display: flex; align-items: baseline; justify-content: space-between; gap: var(--spacing-md); margin-bottom: var(--spacing-md); }
.panel-heading h2 { margin: 0; color: var(--text-primary); font-size: var(--font-size-lg); }
.panel-heading span { color: var(--text-tertiary); font-size: var(--font-size-xs); }
.usage-caption { display: flex; justify-content: center; gap: var(--spacing-xl); color: var(--text-secondary); font-size: var(--font-size-xs); }
.usage-caption i { display: inline-block; width: 8px; height: 8px; margin-right: var(--spacing-xs); border-radius: var(--radius-full); }
.used-dot { background: var(--primary-color); }
.available-dot { background: var(--bg-tertiary); border: 1px solid var(--border-dark); }

@media (max-width: 1024px) {
  .dashboard-grid-main, .dashboard-grid-secondary { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .dashboard-header { align-items: stretch; flex-direction: column; }
  .dashboard-controls, .project-filter { width: 100%; }
  .summary-strip { grid-template-columns: repeat(2, 1fr); }
  .summary-item:nth-child(2) { border-right: 0; }
  .summary-item:nth-child(-n+2) { border-bottom: 1px solid var(--border-light); }
}
@media (max-width: 375px) {
  .dashboard-controls { align-items: stretch; flex-direction: column; }
  .summary-strip { grid-template-columns: 1fr; }
  .summary-item { border-right: 0; border-bottom: 1px solid var(--border-light); }
  .summary-item:last-child { border-bottom: 0; }
  .panel-heading { align-items: flex-start; flex-direction: column; }
}

@include mobile {
  .dashboard-page-header {
    flex-direction: column;
  }
}
</style>
