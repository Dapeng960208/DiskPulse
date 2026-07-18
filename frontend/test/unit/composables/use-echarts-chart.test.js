import { defineComponent, h, nextTick, onMounted } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const loader = vi.hoisted(() => {
  let resolve;
  let promise;
  const reset = () => {
    promise = new Promise((nextResolve) => {
      resolve = nextResolve;
    });
  };
  reset();
  return {
    get promise() { return promise; },
    resolve: (value) => resolve(value),
    reset,
  };
});
const echarts = vi.hoisted(() => ({ init: vi.fn() }));

vi.mock('@/lib/echarts.js', () => ({ loadEcharts: () => loader.promise }));

import { useEchartsChart } from '@/composables/use-echarts-chart.js';

const Harness = defineComponent({
  setup() {
    const { chartDom, initChart } = useEchartsChart();
    onMounted(initChart);
    return () => h('div', { ref: chartDom });
  },
});

describe('useEchartsChart', () => {
  beforeEach(() => {
    echarts.init.mockReset();
    loader.reset();
  });

  it('does not initialize a chart after the component unmounts during lazy loading', async () => {
    const wrapper = mount(Harness, { attachTo: document.body });
    await nextTick();

    wrapper.unmount();
    loader.resolve(echarts);
    await flushPromises();

    expect(echarts.init).not.toHaveBeenCalled();
  });
});
