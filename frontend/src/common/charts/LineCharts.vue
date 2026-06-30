<script setup>
import { onMounted, watch } from 'vue';
import AnimatedTextChart from './AnimatedTextChart.vue'
import { useEchartsChart } from '@/composables/use-echarts-chart';
import { getThemeVar } from '@/lib/echarts';
const props = defineProps({
  data: {
    type: Array,
    default: () => [],
  },
  width: {
    type: String,
    default: '1000px',
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
    default: ''
  },
  showStats: {
    type: Boolean,
    default: false
  },
  threshold: {
    type: Number,
    default: null
  },
  legendName:{
    type:String,
    default:null
  }
});

const { chartDom, initChart, bindWindowResize } = useEchartsChart();

async function renderChart() {
  if (props.data && props.data.length > 0) {
    const context = await initChart();
    if (!context) return;
    const { chart, echarts } = context;
    const option = getOption(props.data, echarts);

    chart.showLoading();
    chart.setOption(option);
    chart.hideLoading();
  }
}

function getOption(data, echarts) {
  const primaryColor = getThemeVar('--chart-color-primary', 'rgb(1, 191, 236)');
  const successColor = getThemeVar('--chart-color-success', 'rgb(128, 255, 165)');
  const seriesData = {
    name:props.legendName,
    type: 'line',
    smooth: true,
    showSymbol: false,
    lineStyle: {
      width: 1,
      color: primaryColor,
    },
    areaStyle: {
      opacity: 0.8,
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        {
          offset: 0,
          color: successColor,
        },
        {
          offset: 1,
          color: primaryColor,
        },
      ]),
    },
    emphasis: {
      focus: 'series',
    },
  };

  if (props.showStats) {
    seriesData.markPoint = {
      symbol: 'pin',
      symbolSize: 30,
      label: {
        position: 'top',
        distance: 5
      },
      data: [
        {
          type: 'max',
          name: '最大值',
          label: {
            formatter: `最大值：{c} ${props.yAxisUnit}`
          },
        },
        {
          type: 'min',
          name: '最小值',
          label: {
            formatter: `最小值：{c} ${props.yAxisUnit}`
          },
        },
      ],
    };
  }

  const option = {
    title: {
      bottom:0,
      text: props.title,
      left: 'center',
      textStyle:{
        color:getThemeVar('--primary-color', '#409eff')
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: getThemeVar('--text-secondary', '#6a7985'),
        },
      },
    },
    legend: {
      show:true,
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
          let result = `${params[0].axisValueLabel}<br/>`;
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
    dataset: {
      source: data,
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
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
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
    series: [seriesData],
  };

  if (props.threshold !== null) {
    option.series[0].markLine = {
      symbol: 'none', // 不显示起始和结束箭头
      data: [
        {
          yAxis: props.threshold,
          label: {
            formatter: `80%`
          },
          lineStyle: {
            type: 'dashed',
            color: getThemeVar('--danger-color', '#EF4444')
          }
        }
      ]
    };
  }

  return option;
}

onMounted(() => {
    renderChart();
    bindWindowResize();
});

watch(() => props.width, renderChart);
watch(() => props.height, renderChart);
watch(() => props.data, renderChart, { deep: true });
// watch(() => props.title, renderChart);

</script>

<template>
  <AnimatedTextChart
    v-if="!props.data || props.data.length === 0"
    :text="'NO DATA'"></AnimatedTextChart>
  <div
    v-else
    ref="chartDom"
    :style="{ width: props.width, height: props.height }"></div>
</template>
