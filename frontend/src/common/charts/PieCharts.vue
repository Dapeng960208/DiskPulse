<template>
  <div
    ref="chartDom"
    :style="{ width: props.width, height: props.height }"></div>
</template>

<script setup>
import { onMounted, watch } from 'vue';
import { useEchartsChart } from '@/composables/use-echarts-chart';
import { getChartColors } from '@/lib/echarts';

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
    default: () => [],
  },
  title: {
    type: String,
    default: 'Nightingale Chart',
  }
});

const { chartDom, initChart, bindWindowResize } = useEchartsChart();

async function renderChart() {
  if (!chartDom.value || !props.data || props.data.length===0 ) return;

  const context = await initChart();
  if (!context) return;
  const { chart } = context;
  const option = {
    color: getChartColors(),
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

</script>
