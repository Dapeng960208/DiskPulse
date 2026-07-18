import { onBeforeUnmount, ref } from 'vue';
import { loadEcharts } from '@/lib/echarts';

export function useEchartsChart() {
  const chartDom = ref(null);
  let chartInstance = null;
  let resizeBound = false;
  let active = true;
  let renderGeneration = 0;

  async function initChart() {
    if (!chartDom.value) return null;
    const generation = ++renderGeneration;

    if (chartInstance) {
      chartInstance.dispose();
      chartInstance = null;
    }

    const echarts = await loadEcharts();
    // Review fix: ignore lazy-load completions from an unmounted or superseded chart render.
    if (!active || generation !== renderGeneration || !chartDom.value) return null;
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
    active = false;
    renderGeneration += 1;
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
