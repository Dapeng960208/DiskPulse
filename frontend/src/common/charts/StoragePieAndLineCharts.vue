<script setup>
import { onMounted, ref, watch, onBeforeUnmount, nextTick } from 'vue';
import * as echarts from 'echarts';

// 定义组件的属性
const props = defineProps({
  data: {
    type: Array,
    required: true,
  },
  width: {
    type: String,
    default: '100%',
  },
  height: {
    type: String,
    default: '600px',
  },
  title: {
    type: String,
    default: '折线图',
  },
  yAxisUnit: {
    type: String,
    default: '',
  },
});

const chartDom = ref(null);
let chartInstance = null;

// 渲染图表
function renderChart() {
  if (!props.data || props.data.length === 0) return;

  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(chartDom.value);
  const option = getOption();

  chartInstance.showLoading();
  chartInstance.on('updateAxisPointer', (event) => {
    const xAxisInfo = event.axesInfo[0];
    if (xAxisInfo) {
      const dimension = xAxisInfo.value + 1;
      chartInstance.setOption({
        series: {
          id: 'pie',
          label: {
            formatter: `{b}: {@[${dimension}]} ${props.yAxisUnit} ({d}%)`
          },
          encode: {
            value: dimension,
            tooltip: dimension
          }
        }
      });
    }
  });
  chartInstance.setOption(option);
  chartInstance.hideLoading();
}

// 获取图表配置项
function getOption() {
  const lineSeries = props.data.slice(0, -1).map(() => ({
    type: 'line',
    smooth: true,
    seriesLayoutBy: 'row',
    emphasis: { focus: 'series' }
  }));


  const pieSeries = {
    type: 'pie',
    id: 'pie',
    radius: '30%',
    center: ['50%', '25%'],
    emphasis: { focus: 'self' },
    label: {
      formatter: `{b}: {@[1]} ${props.yAxisUnit} ({d}%)`
    },
    encode: {
      itemName: 'project',
      value: 1,
      tooltip: 1
    }
  };

  return {
    title: {
      text: props.title,
      left: 'left',
    },
    legend: {},
    tooltip: {
      trigger: 'axis',
      showContent: false
    },
    dataset: {
      source: props.data
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
    xAxis: { type: 'category' },
    yAxis: {
      gridIndex: 0,
      axisLabel: {
        formatter: `{value} ${props.yAxisUnit}`,
      },
    },
    grid: { top: '55%' },
    series: [...lineSeries, pieSeries]
  };
}

// 调整图表大小
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

<template>
  <div
    ref="chartDom"
    :style="{ width: props.width, height: props.height }"></div>
</template>
