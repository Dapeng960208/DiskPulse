import { onBeforeUnmount, ref } from 'vue';
import { loadEcharts } from '@/lib/echarts';

export function useEchartsChart() {
  const chartDom = ref(null);
  let chartInstance = null;
  let resizeBound = false;

  async function initChart() {
    if (!chartDom.value) return null;

    if (chartInstance) {
      chartInstance.dispose();
    }

    const echarts = await loadEcharts();
    chartInstance = echarts.init(chartDom.value);

    return { chart: chartInstance, echarts };
  }

  function resizeChart() {
    chartInstance?.resize();
  }

  function bindWindowResize() {
    if (resizeBound) return;
    window.addEventListener('resize', resizeChart, { passive: true });
    resizeBound = true;
  }

  function disposeChart() {
    if (resizeBound) {
      window.removeEventListener('resize', resizeChart);
      resizeBound = false;
    }

    chartInstance?.dispose();
    chartInstance = null;
  }

  onBeforeUnmount(disposeChart);

  return {
    chartDom,
    initChart,
    resizeChart,
    bindWindowResize,
    disposeChart,
  };
}
