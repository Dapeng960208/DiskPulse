import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const chart = {
  setOption: vi.fn(),
  resize: vi.fn(),
  dispose: vi.fn(),
};
const echarts = { init: vi.fn(() => chart) };

vi.mock('@/lib/echarts.js', () => ({ loadECharts: vi.fn(async () => echarts) }));

describe('DashboardChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('lazily renders, resizes, updates and disposes the chart', async () => {
    const { default: DashboardChart } = await import('@/components/dashboard/DashboardChart.vue');
    const wrapper = mount(DashboardChart, {
      props: {
        option: { series: [{ data: [1] }] },
        ariaLabel: '容量趋势',
      },
    });
    await vi.waitFor(() => expect(echarts.init).toHaveBeenCalledTimes(1));

    expect(chart.setOption).toHaveBeenCalledWith({ series: [{ data: [1] }] }, true);
    expect(wrapper.attributes('aria-label')).toBe('容量趋势');

    window.dispatchEvent(new Event('resize'));
    expect(chart.resize).toHaveBeenCalledTimes(1);

    await wrapper.setProps({ option: { series: [{ data: [2] }] } });
    expect(chart.setOption).toHaveBeenLastCalledWith({ series: [{ data: [2] }] }, true);

    wrapper.unmount();
    expect(chart.dispose).toHaveBeenCalledTimes(1);
  });
});
