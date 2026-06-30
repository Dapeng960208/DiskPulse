<script setup>
import { onMounted, ref, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  text: {
    type: String,
    required: true,
  },
  width: {
    type: String,
    default: '1200px',
  },
  height: {
    type: String,
    default: '800px',
  },
  fontSize: {
    type: Number,
    default: 120,
  },
  fontWeight: {
    type: String,
    default: 'bold',
  },
  strokeColor: {
    type: String,
    default: '#409eff',
  },
  fillColor: {
    type: String,
    default: '#a0cfff',
  },
  animationDuration: {
    type: Number,
    default: 3000,
  },
});

const chartDom = ref(null);
let chartInstance = null;


function renderChart() {
  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(chartDom.value);

  const option = {
    graphic: {
      elements: [
        {
          type: 'text',
          left: 'center',
          top: 'center',
          style: {
            text: props.text,
            fontSize: props.fontSize,
            fontWeight: props.fontWeight,
            lineDash: [0, 200],
            lineDashOffset: 0,
            fill: 'transparent',
            stroke: props.strokeColor,
            lineWidth: 2
          },
          keyframeAnimation: {
            duration: props.animationDuration,
            loop: true,
            keyframes: [
              {
                percent: 0.7,
                style: {
                  fill: 'transparent',
                  lineDashOffset: 200,
                  lineDash: [200, 0]
                }
              },
              {
                percent: 0.8,
                style: {
                  fill: 'transparent'
                }
              },
              {
                percent: 1,
                style: {
                  fill: props.fillColor
                }
              }
            ]
          }
        }
      ]
    }
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
watch(() => props.text, renderChart);

</script>
<template>
  <div
    ref="chartDom"
    :style="{ width: props.width, height: props.height }"></div>
</template>

