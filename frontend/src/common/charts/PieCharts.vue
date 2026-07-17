<template>
  <div
    ref="chartDom"
    :style="{ width: props.width, height: props.height }"></div>
</template>

<script setup>
import { onMounted, watch } from 'vue';
import { useEchartsChart } from '@/composables/use-echarts-chart';
import { getChartColors, getThemeVar } from '@/lib/echarts';

const props = defineProps({
  width: {
    type: String,
    default: '100%',
  },
  height: {
    type: String,
    default: '600px',
  },
  data: {
    type: Array,
    required: true,
  },
  title: {
    type: String,
    default: 'Nightingale Chart',
  },
  variant: {
    type: String,
    default: 'rose',
  },
  centerLabel: {
    type: String,
    default: '',
  },
});

const { chartDom, initChart, bindWindowResize } = useEchartsChart();

async function renderChart() {
  if (!chartDom.value || !props.data?.length) return;

  const context = await initChart();
  if (!context) return;

  const { chart } = context;
  const isDashboard = props.variant === 'dashboard';
  const color = (name, fallback) => getThemeVar(name, fallback);
  const option = {
    color: isDashboard
      ? [color('--primary-color', '#3B82F6'), color('--bg-tertiary', '#F1F5F9')]
      : getChartColors(),
    legend: {
      top: 'bottom',
      show: !isDashboard,
    },
    toolbox: {
      show: !isDashboard,
      feature: {
        mark: { show: true },
        dataView: { show: true, readOnly: false },
        restore: { show: true },
        saveAsImage: { show: true },
      },
    },
    dataset: isDashboard ? undefined : { source: props.data },
    title: isDashboard ? {
      text: props.centerLabel,
      subtext: '已使用',
      left: 'center',
      top: '38%',
      textStyle: { color: color('--text-primary', '#1E293B'), fontSize: 24, fontWeight: 700 },
      subtextStyle: { color: color('--text-secondary', '#64748B'), fontSize: 12 },
    } : undefined,
    tooltip: {
      trigger: 'item',
    },
    series: [
      {
        name: props.title,
        type: 'pie',
        radius: isDashboard ? ['68%', '86%'] : [20, 140],
        center: ['50%', '50%'],
        roseType: isDashboard ? undefined : 'radius',
        data: isDashboard ? props.data : undefined,
        itemStyle: {
          borderRadius: isDashboard ? 10 : 5,
          borderColor: color('--bg-primary', '#FFFFFF'),
          borderWidth: isDashboard ? 3 : 0,
        },
        label: {
          show: !isDashboard,
        },
        emphasis: {
          label: {
            show: true,
          },
        },
      },
    ],
  };

  chart.setOption(option);
}

onMounted(() => {
  renderChart();
  bindWindowResize();
});

watch(() => props.width, renderChart);
watch(() => props.height, renderChart);
watch(() => props.data, renderChart, { deep: true });
watch(() => props.title, renderChart);
watch(() => props.variant, renderChart);
watch(() => props.centerLabel, renderChart);
</script>
