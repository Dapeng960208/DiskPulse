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
    default: () => [],
  },
  categories: {
    type: Array,
    default: () => [],
  },
  seriesNames: {
    type: Array,
    default: () => [],
  },
  seriesMap: {
    type: Object,
    default:()=>({}),
  },
  title: {
    type: String,
    default: 'Chart Title',
  },
  unit: {
    type: String,
    default: 'T',
  }
});

const { chartDom, initChart, bindWindowResize } = useEchartsChart();

function calculateTotalData(rawData) {
  if (!rawData.length) return [];

  const totalData = [];
  for (let i = 0; i < rawData[0].length; ++i) {
    let sum = 0;
    for (let j = 0; j < rawData.length; ++j) {
      sum += rawData[j][i];
    }
    totalData.push(sum);
  }
  return totalData;
}

function createSeries(rawData, totalData, seriesNames) {

  return seriesNames.map((name, sid) => {
    const mappedName = props.seriesMap[name] || name;
    return {
      name:mappedName,
      type: 'bar',
      stack: 'total',
      barWidth: '60%',
      barMaxWidth: 100,
      label: {
        show: true,
        formatter: (params) => `${Math.round(params.value)}${props.unit}`
      },
      data: rawData[sid].map((d, did) =>
        totalData[did] <= 0 ? 0 : d
      )
    };
  });
}

async function renderChart() {
  if (!chartDom.value) return;

  const context = await initChart();
  if (!context) return;
  const { chart } = context;

  const totalData = calculateTotalData(props.data);
  const series = createSeries(props.data, totalData, props.seriesNames);

  const option = {
    color: getChartColors(),
    title: {
      bottom: 0,
      text: props.title,
      left: 'center',
      textStyle: {
        color: getThemeVar('--primary-color', '#409eff')
      }
    },
    legend: {
      selectedMode: false
    },
    grid: {
      left: 100,
      right: 100,
      top: 50,
      bottom: 80
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
    yAxis: {
      type: 'value'
    },
    xAxis: {
      type: 'category',
      data: props.categories,
      axisLabel: {
        rotate: 45, // Rotate the labels 45 degrees
        interval: 0, // Show all labels
        formatter: function (value) {
          return value.length > 10 ? value.slice(0, 10) + '...' : value; // Optional: truncate long labels
        }
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function (params) {
        let tooltipText = `${params[0].axisValue}<br/>`;
        params.forEach(param => {
          tooltipText += `${param.marker} ${param.seriesName}: ${param.value}${props.unit}<br/>`;
        });
        return tooltipText;
      }
    },
    series
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
watch(() => props.categories, renderChart, { deep: true });
watch(() => props.seriesNames, renderChart, { deep: true });

</script>

<template>
  <div
    ref="chartDom"
    :style="{ width: props.width, height: props.height }"></div>
</template>
