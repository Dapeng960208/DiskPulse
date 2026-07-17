<script setup>
import { onMounted, watch } from 'vue';
import { useEchartsChart } from '@/composables/use-echarts-chart';
import { getThemeVar, prefersReducedMotion } from '@/lib/echarts';

const props = defineProps({
  width: {
    type: String,
    default: '1200px',
  },
  height: {
    type: String,
    default: '100%',
  },
});

const { chartDom, initChart, bindWindowResize } = useEchartsChart();

function getOption() {
  const reducedMotion = prefersReducedMotion();
  return {
  graphic: {
    elements: [
      {
        type: 'group',
        left: 'center',
        top: 'center',
        children: new Array(7).fill(0).map((val, i) => ({
          type: 'rect',
          x: i * 20,
          shape: {
            x: 0,
            y: -40,
            width: 10,
            height: 80,
          },
          style: {
            fill: getThemeVar('--chart-color-primary', '#5470c6'),
          },
          keyframeAnimation: {
            duration: reducedMotion ? 0 : 1000,
            delay: i * 200,
            loop: true,
            keyframes: [
              {
                percent: 0.5,
                scaleY: 0.3,
                easing: 'cubicIn',
              },
              {
                percent: 1,
                scaleY: 1,
                easing: 'cubicOut',
              },
            ],
          },
        })),
      },
    ],
  },
};
}


async function renderChart() {
  if (!chartDom.value) return;

  const context = await initChart();
  if (!context) return;
  context.chart.setOption(getOption());
}

// 监听 props 的变化
onMounted(() => {
    renderChart();
    bindWindowResize();
});

watch(() => props.width, renderChart);
watch(() => props.height, renderChart);

</script>

<template>
  <div
    ref="chartDom"
    :style="{ width: props.width, height: props.height }"></div>
</template>
