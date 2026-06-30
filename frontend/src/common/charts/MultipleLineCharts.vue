<template>
  <div
    ref="chartDom"
    :style="{ width: width, height: height }"></div>
</template>

<script setup>
import { onMounted, watch } from 'vue';
import { useEchartsChart } from '@/composables/use-echarts-chart';
import { getChartColors, getThemeVar } from '@/lib/echarts';

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  width: {
    type: String,
    default: '100%',
  },
  height: {
    type: String,
    default: '400px',
  },
  title: {
    type: String,
    default: '',
  },
  yAxisUnit: {
    type: String,
    default: '',
  },
});

const { chartDom, initChart, bindWindowResize } = useEchartsChart();

const renderChart = async () => {
  const context = await initChart();
  if (!context) return;
  const { chart } = context;
  const option = getOption(props.data);
  chart.setOption(option);
};

const createSeries = (data) => {
  return Object.keys(data).map(key => {
    return {
      name: key,
      type: 'line',
      smooth: true,
      showSymbol: false,
      emphasis: {
        focus: 'series',
      },
      data: data[key],
    };
  });
};

const formatDate = (date) => {
  const d = new Date(date);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd} ${hh}:${min}:00`;
};

const getOption = (data) => {
  const seriesData = createSeries(data);
  const option = {
    color: getChartColors(),
    title: {
      text: props.title,
      left: 'center',
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: getThemeVar('--text-secondary', '#6a7985'),
        },
      },
      formatter: (params) => {
        if (Array.isArray(params)) {
          let result = `${formatDate(params[0].axisValueLabel)}<br/>`;
          params.forEach((item) => {
            let value = item.data[1];
            let unit = props.yAxisUnit;
            if (props.yAxisUnit === 'G') {
              value = (value / 1024).toFixed(2); // G 转换为 T 并保留两位小数
              unit = 'T';
            } else {
              value = value.toFixed(2); // 保留两位小数
            }
            result += `${item.marker}${item.seriesName}: ${value} ${unit}<br/>`;
          });
          return result;
        }
        return '';
      },
    },
    legend: {
      data: Object.keys(data),
    },
    toolbox: {
      feature: {
        saveAsImage: {},
      },
    },
    xAxis: {
      type: 'time',
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: `{value} ${props.yAxisUnit}`,
      },
    },
    series: seriesData,
  };
  return option;
};

onMounted(() => {
  renderChart();
  bindWindowResize();
});

watch(() => props.data, renderChart, { deep: true });
</script>
