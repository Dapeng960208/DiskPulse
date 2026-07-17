<template>
  <div
    ref="chartDom"
    :style="{ width: props.width, height: props.height }"></div>
</template>

<script setup>
import { onMounted, ref, watch, onBeforeUnmount, nextTick } from 'vue';
import * as echarts from 'echarts';

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

const chartDom = ref(null);
let chartInstance = null;

function renderChart() {
  if (!chartDom.value || !props.data || props.data.length===0 ) return;

  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(chartDom.value);
  const isDashboard = props.variant === 'dashboard';
  const styles = getComputedStyle(document.documentElement);
  const color = (name, fallback) => styles.getPropertyValue(name).trim() || fallback;
  const option = {
    color: isDashboard
      ? [color('--primary-color', '#3B82F6'), color('--bg-tertiary', '#F1F5F9')]
      : undefined,
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
        saveAsImage: { show: true }
      }
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
        show: !isDashboard
      },
      emphasis: {
        label: {
          show: true
        }
      },
      }
    ]
  };

  chartInstance.setOption(option);
}

function resizeChart() {
  if (chartInstance) {
    chartInstance.resize();
  }
}

onMounted(() => {
    renderChart();
    window.addEventListener('resize', resizeChart, { passive: true });
});

watch(() => props.width, renderChart);
watch(() => props.height, renderChart);
watch(() => props.data, renderChart, { deep: true });
watch(() => props.title, renderChart);
watch(() => props.variant, renderChart);
watch(() => props.centerLabel, renderChart);

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart);
  chartInstance?.dispose();
});

</script>
