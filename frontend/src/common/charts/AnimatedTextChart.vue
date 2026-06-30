<script setup>
import { onMounted, watch } from 'vue';
import { useEchartsChart } from '@/composables/use-echarts-chart';
import { getThemeVar, prefersReducedMotion } from '@/lib/echarts';

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

const { chartDom, initChart, bindWindowResize } = useEchartsChart();

async function renderChart() {
  const context = await initChart();
  if (!context) return;
  const { chart } = context;
  const animationDuration = prefersReducedMotion() ? 0 : props.animationDuration;

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
            stroke: props.strokeColor || getThemeVar('--chart-color-primary', '#409eff'),
            lineWidth: 2
          },
          keyframeAnimation: {
            duration: animationDuration,
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
                  fill: props.fillColor || getThemeVar('--chart-color-info', '#a0cfff')
                }
              }
            ]
          }
        }
      ]
    }
  };

  chart.setOption(option);
}

onMounted(() => {
    renderChart();
    bindWindowResize();
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

