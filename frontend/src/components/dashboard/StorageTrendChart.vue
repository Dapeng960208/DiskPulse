<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { getChartColors, getCssColor, loadECharts } from '@/lib/echarts.js';
import { buildStorageTrendOption } from '@/utils/storage-trend-chart.js';

const props = defineProps({
  series: { type: Array, required: true },
  indicator: { type: String, default: 'used' },
  trendMeta: { type: Object, default: null },
  systemThresholds: { type: Object, default: null },
  unit: { type: String, default: '' },
  ariaLabel: { type: String, required: true },
  height: { type: String, default: '420px' },
});

const chartDom = ref(null);
let chart;
let resizeObserver;
let themeObserver;
let active = true;

function token(name, fallback) {
  return getCssColor(name, fallback);
}

function palette() {
  return {
    normal: token('--chart-color-normal', '#446AEE'),
    important: token('--chart-color-important', '#D69B1E'),
    serious: token('--chart-color-serious', '#EF5923'),
    emergency: token('--chart-color-emergency', '#D3372F'),
    grid: token('--border-light', '#F1F5F9'),
    axis: token('--text-tertiary', '#94A3B8'),
    surface: token('--bg-primary', '#FFFFFF'),
    series: getChartColors(),
  };
}

function setOption() {
  if (!chart) return;
  chart.setOption(buildStorageTrendOption({
    series: props.series,
    indicator: props.indicator,
    trendMeta: props.trendMeta,
    systemThresholds: props.systemThresholds,
    unit: props.unit || undefined,
    palette: palette(),
  }), true);
}

async function initChart() {
  const echarts = await loadECharts();
  if (!active || !chartDom.value) return;
  chart = echarts.init(chartDom.value);
  setOption();
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => chart?.resize());
    resizeObserver.observe(chartDom.value);
  }
  themeObserver = new MutationObserver(setOption);
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
}

onMounted(() => nextTick(initChart));

watch(
  () => [props.series, props.indicator, props.trendMeta, props.systemThresholds, props.unit],
  setOption,
  { deep: true },
);

onBeforeUnmount(() => {
  active = false;
  resizeObserver?.disconnect();
  themeObserver?.disconnect();
  chart?.dispose();
});
</script>

<template>
  <div
    ref="chartDom"
    class="storage-trend-chart"
    role="img"
    :aria-label="ariaLabel"
    :style="{ height }"></div>
</template>

<style scoped>
.storage-trend-chart {
  width: 100%;
  min-width: 0;
}
</style>
