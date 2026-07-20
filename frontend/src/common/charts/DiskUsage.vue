<script setup>
import { onMounted, watch, nextTick } from 'vue';
import AnimatedTextChart from './AnimatedTextChart.vue'
import { useEchartsChart } from '@/composables/use-echarts-chart';
import { getChartColors, getThemeVar } from '@/lib/echarts';
// 定义组件的属性
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
    default: 'Disk Usage',
  },
  label: {
    type: String,
    default: '存储分布图',
  },
});

const { chartDom, initChart, bindWindowResize } = useEchartsChart();

// 组件挂载时初始化图表
onMounted(() => {
  // setTimeout(() => {
  //   renderChart();
  //   window.addEventListener('resize', resizeChart);
  // }, 1200);
  nextTick(() => {
    renderChart();
    bindWindowResize();
  });
});

// 组件卸载时清理图表实例和事件监听
// 监听数据变化重新渲染图表
watch(() => props.data, () => {
  nextTick(() => {
    renderChart();
  });
}, { deep: true });

// 渲染图表
async function renderChart() {
  if (!props.data || props.data.length === 0) return;
  if (!chartDom.value || !chartDom.value.clientWidth ||!chartDom.value.clientHeight) return;

  const context = await initChart();
  if (!context) return;
  const { chart, echarts } = context;
  chart.showLoading();

  const formatUtil = echarts.format;

  function getLevelOption() {
    return [
      {
        itemStyle: {
          borderWidth: 0,
          gapWidth: 5
        }
      },
      {
        itemStyle: {
          gapWidth: 1
        }
      },
      {
        colorSaturation: [0.35, 0.5],
        itemStyle: {
          gapWidth: 1,
          borderColorSaturation: 0.6
        }
      }
    ];
  }

  const option = {
    color: getChartColors(),
    title: {
      text: props.title,
      left: 'center'
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
    tooltip: {
      formatter: function (info) {
        const limit = info.data.limit || '0';
        const used = info.data.used || '0';
        const usedRatio = info.data.used_ratio || '0';

        const treePathInfo = info.treePathInfo;
        const treePath = [];
        for (let i = 1; i < treePathInfo.length; i++) {
          treePath.push(treePathInfo[i].name);
        }

        return [
          '<div class="tooltip-title">' +
            formatUtil.encodeHTML(treePath.join('/')) +
            '</div>',
          '限额: ' + formatUtil.addCommas(limit) + ' TB',
          '使用量: ' + formatUtil.addCommas(used) + ' TB',
          '使用率: ' + usedRatio + '%'
        ].join('<br/>');
      }
    },
    series: [
      {
        name: props.label,
        type: 'treemap',
        visibleMin: 0,
        label: {
          show: true,
          formatter: '{b}'
        },
        itemStyle: {
          borderColor: getThemeVar('--bg-primary', '#fff')
        },
        levels: getLevelOption(),
        data: props.data
      }
    ]
  };

  chart.setOption(option);
  chart.hideLoading();
}

// 调整图表大小
</script>

<template>
  <div
    ref="chartDom"
    :style="{ width: props.width, height: props.height } "></div>
</template>
