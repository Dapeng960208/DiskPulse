<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { loadECharts } from '@/lib/echarts.js';

const props = defineProps({
  option: { type: Object, required: true },
  ariaLabel: { type: String, required: true },
  height: { type: String, default: '280px' },
});

const chartDom = ref(null);
let chartInstance;
let active = true;

async function initChart() {
  const echarts = await loadECharts();
  if (!active || !chartDom.value) return;
  chartInstance = echarts.init(chartDom.value);
  chartInstance.setOption(props.option, true);
}

function resizeChart() {
  chartInstance?.resize();
}

onMounted(() => {
  nextTick(initChart);
  window.addEventListener('resize', resizeChart, { passive: true });
});

watch(() => props.option, (option) => chartInstance?.setOption(option, true), { deep: true });

onBeforeUnmount(() => {
  active = false;
  window.removeEventListener('resize', resizeChart);
  chartInstance?.dispose();
});
</script>

<template>
  <div
    ref="chartDom"
    class="dashboard-chart"
    role="img"
    :aria-label="ariaLabel"
    :style="{ height }" />
</template>

<style scoped>
.dashboard-chart { width: 100%; min-width: 0; }
</style>
