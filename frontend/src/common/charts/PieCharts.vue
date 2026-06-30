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
  }
});

const chartDom = ref(null);
let chartInstance = null;

function renderChart() {
  if (!chartDom.value || !props.data || props.data.length===0 ) return;

  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(chartDom.value);
  const option = {
    legend: {
      top: 'bottom'
    },
    toolbox: {
      show: true,
      feature: {
        mark: { show: true },
        dataView: { show: true, readOnly: false },
        restore: { show: true },
        saveAsImage: { show: true }
      }
    },
    dataset: {
      source: props.data
    },
    tooltip: {
      trigger: 'item',
    },
    series: [
      {
        name: props.title,
        type: 'pie',
        radius: [20, 140],
        center: ['50%', '50%'],
        roseType: 'radius',
        itemStyle: {
        borderRadius: 5
      },
      label: {
        show: true
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

</script>
