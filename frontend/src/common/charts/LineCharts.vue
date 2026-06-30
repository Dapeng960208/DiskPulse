<script setup>
import { onMounted, ref, watch, onBeforeUnmount, nextTick } from 'vue';
import * as echarts from 'echarts';
import AnimatedTextChart from './AnimatedTextChart.vue'
const props = defineProps({
  data: {
    type: Array,
    required: true,
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

const chartDom = ref(null);
let chartInstance = null;

function renderChart() {
  if (props.data && props.data.length > 0) {
    if (chartInstance) {
      chartInstance.dispose();
    }
    chartInstance = echarts.init(chartDom.value);
    const option = getOption(props.data);

    chartInstance.showLoading();
    chartInstance.setOption(option);
    chartInstance.hideLoading();
  }
}

function getOption(data) {
  console.log(props.legendName);

  const seriesData = {
    name:props.legendName,
    type: 'line',
    smooth: true,
    showSymbol: false,
    lineStyle: {
      width: 1,
      color: 'rgb(1, 191, 236)',
    },
    areaStyle: {
      opacity: 0.8,
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        {
          offset: 0,
          color: 'rgb(128, 255, 165)',
        },
        {
          offset: 1,
          color: 'rgb(1, 191, 236)',
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
        color:'#409eff'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985',
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
          backgroundColor: '#6a7985',
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
            color: 'red'
          }
        }
      ]
    };
  }

  return option;
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
