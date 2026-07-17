<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { ElEmpty, ElMessage, ElSkeleton } from 'element-plus';
import dashboardApi from '@/api/dashboard-api.js';
import PieCharts from '@/common/charts/PieCharts.vue';
import DashboardChart from '@/components/dashboard/DashboardChart.vue';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import { getCssColor } from '@/lib/echarts.js';

const projectId = ref(null);
const overview = ref(null);
const loading = ref(true);
let requestId = 0;

const token = (name, fallback) => getCssColor(name, fallback);
const primary = () => token('--primary-color', '#3B82F6');
const primaryLight = () => token('--primary-lighter', '#93C5FD');
const warning = () => token('--warning-color', '#F59E0B');
const gridColor = () => token('--border-light', '#F1F5F9');
const axisColor = () => token('--text-tertiary', '#94A3B8');

const isProject = computed(() => overview.value?.scope.mode === 'project');
const limitLabel = computed(() => (isProject.value ? '项目限额' : '物理总容量'));
const comparisonTitle = computed(() => (isProject.value ? '项目组容量对比' : '项目容量对比'));
const summary = computed(() => overview.value?.summary || {});
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

function dateLabel(value) {
  return String(value).slice(5, 10).replace('-', '/');
}

const lineOption = computed(() => ({
  animationDuration: 500,
  tooltip: { trigger: 'axis', valueFormatter: (value) => formatCapacity(value) },
  grid: { left: 16, right: 16, top: 24, bottom: 12, containLabel: true },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: (overview.value?.capacity_trend || []).map((item) => dateLabel(item.timestamp)),
    axisLine: { lineStyle: { color: gridColor() } },
    axisTick: { show: false },
    axisLabel: { color: axisColor(), hideOverlap: true },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: axisColor(), formatter: (value) => formatCapacity(value) },
    splitLine: { lineStyle: { color: gridColor(), type: 'dashed' } },
  },
  series: [{
    name: '已使用',
    type: 'line',
    smooth: true,
    showSymbol: false,
    lineStyle: { width: 3, color: primary() },
    areaStyle: { color: primaryLight(), opacity: 0.22 },
    data: (overview.value?.capacity_trend || []).map((item) => item.used_gb),
  }],
}));

const comparisonOption = computed(() => {
  const items = overview.value?.capacity_items || [];
  return {
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
      data: items.map((item) => item.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: axisColor(), width: 100, overflow: 'truncate' },
    },
    series: [
      { name: '已使用', type: 'bar', stack: 'capacity', barWidth: 14, itemStyle: { color: primary(), borderRadius: [4, 0, 0, 4] }, data: items.map((item) => item.used_gb) },
      { name: '可使用', type: 'bar', stack: 'capacity', barWidth: 14, itemStyle: { color: primaryLight(), borderRadius: [0, 4, 4, 0] }, data: items.map((item) => item.available_gb) },
    ],
  };
});

const alertOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 12, right: 12, top: 18, bottom: 12, containLabel: true },
  xAxis: {
    type: 'category',
    data: (overview.value?.alert_trend || []).map((item) => dateLabel(item.date)),
    axisLine: { lineStyle: { color: gridColor() } },
    axisTick: { show: false },
    axisLabel: { color: axisColor(), hideOverlap: true },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    axisLabel: { color: axisColor() },
    splitLine: { lineStyle: { color: gridColor(), type: 'dashed' } },
  },
  series: [{
    name: '告警',
    type: 'bar',
    barMaxWidth: 16,
    itemStyle: { color: warning(), borderRadius: [4, 4, 0, 0] },
    data: (overview.value?.alert_trend || []).map((item) => item.count),
  }],
}));

async function loadOverview() {
  const currentRequest = ++requestId;
  loading.value = true;
  try {
    const params = projectId.value ? { project_id: projectId.value } : {};
    const result = await dashboardApi.fetchOverview(params);
    if (currentRequest === requestId) overview.value = result;
  } catch {
    if (currentRequest === requestId) {
      overview.value = null;
      ElMessage.error('加载存储概览失败，请稍后重试');
    }
  } finally {
    if (currentRequest === requestId) loading.value = false;
  }
}

watch(projectId, loadOverview);
onMounted(loadOverview);
</script>

<template>
  <main class="dashboard-page">
    <header class="dashboard-header">
      <div>
        <h1>存储概览</h1>
        <p>{{ isProject ? overview?.scope.project_name : '全局存储运行视图' }}</p>
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

    <ElSkeleton
      v-if="loading"
      class="dashboard-skeleton"
      :rows="8"
      animated />

    <ElEmpty
      v-else-if="!overview"
      class="dashboard-empty"
      description="暂无概览数据" />

    <template v-else>
      <section class="summary-strip" aria-label="容量摘要">
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
      </section>

      <section class="dashboard-grid dashboard-grid-main">
        <article class="dashboard-panel trend-panel">
          <div class="panel-heading">
            <h2>容量趋势</h2>
            <span>已使用容量</span>
          </div>
          <DashboardChart
            v-if="overview.capacity_trend.length"
            :option="lineOption"
            aria-label="近 30 天容量趋势" />
          <ElEmpty v-else description="暂无容量趋势" />
        </article>

        <article class="dashboard-panel usage-panel">
          <div class="panel-heading">
            <h2>容量使用率</h2>
            <span>{{ summary.storage_cluster_count }} 个存储集群</span>
          </div>
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
        </article>
      </section>

      <section class="dashboard-grid dashboard-grid-secondary">
        <article class="dashboard-panel comparison-panel">
          <div class="panel-heading">
            <h2>{{ comparisonTitle }}</h2>
            <span>按已使用容量 Top 10</span>
          </div>
          <DashboardChart
            v-if="overview.capacity_items.length"
            :option="comparisonOption"
            :aria-label="comparisonTitle"
            height="320px" />
          <ElEmpty v-else description="暂无容量对比数据" />
        </article>

        <article class="dashboard-panel alert-panel">
          <div class="panel-heading">
            <h2>告警趋势</h2>
            <span>每日触发数</span>
          </div>
          <DashboardChart
            :option="alertOption"
            aria-label="近 30 天告警趋势"
            height="320px" />
        </article>
      </section>
    </template>
  </main>
</template>

<style lang="scss" scoped>
.dashboard-page { display: grid; gap: var(--spacing-xl); min-width: 0; padding: var(--spacing-2xl); background: var(--bg-secondary); }
.dashboard-header { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--spacing-xl); }
.dashboard-header h1 { margin: 0; color: var(--text-primary); font-size: var(--font-size-3xl); line-height: var(--line-height-tight); }
.dashboard-header p { margin: var(--spacing-xs) 0 0; color: var(--text-secondary); font-size: var(--font-size-sm); }
.dashboard-controls { display: flex; align-items: center; gap: var(--spacing-md); }
.project-filter { width: 240px; }
.period-chip { flex: none; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-primary); color: var(--text-secondary); font-size: var(--font-size-sm); }
.summary-strip { display: grid; grid-template-columns: repeat(4, 1fr); overflow: hidden; border: 1px solid var(--border-color); border-radius: var(--radius-lg); background: var(--bg-primary); box-shadow: var(--shadow-xs); }
.summary-item { display: grid; gap: var(--spacing-sm); padding: var(--spacing-xl) var(--spacing-2xl); border-right: 1px solid var(--border-light); }
.summary-item:last-child { border-right: 0; }
.summary-item span { color: var(--text-secondary); font-size: var(--font-size-sm); }
.summary-item strong { color: var(--text-primary); font-size: var(--font-size-2xl); line-height: 1; }
.summary-alert strong { color: var(--warning-color); }
.dashboard-grid { display: grid; gap: var(--spacing-xl); min-width: 0; }
.dashboard-grid-main { grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr); }
.dashboard-grid-secondary { grid-template-columns: minmax(0, 1.35fr) minmax(340px, 1fr); }
.dashboard-panel { min-width: 0; padding: var(--spacing-xl); border: 1px solid var(--border-color); border-radius: var(--radius-lg); background: var(--bg-primary); box-shadow: var(--shadow-xs); }
.panel-heading { display: flex; align-items: baseline; justify-content: space-between; gap: var(--spacing-md); margin-bottom: var(--spacing-md); }
.panel-heading h2 { margin: 0; color: var(--text-primary); font-size: var(--font-size-lg); }
.panel-heading span { color: var(--text-tertiary); font-size: var(--font-size-xs); }
.usage-caption { display: flex; justify-content: center; gap: var(--spacing-xl); color: var(--text-secondary); font-size: var(--font-size-xs); }
.usage-caption i { display: inline-block; width: 8px; height: 8px; margin-right: var(--spacing-xs); border-radius: var(--radius-full); }
.used-dot { background: var(--primary-color); }
.available-dot { background: var(--bg-tertiary); border: 1px solid var(--border-dark); }
.dashboard-skeleton, .dashboard-empty { padding: var(--spacing-3xl); border: 1px solid var(--border-color); border-radius: var(--radius-lg); background: var(--bg-primary); }

@media (max-width: 1024px) {
  .dashboard-grid-main, .dashboard-grid-secondary { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .dashboard-page { padding: var(--spacing-lg); }
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
</style>
