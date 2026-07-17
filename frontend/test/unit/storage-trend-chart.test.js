import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const chart = {
  dispose: vi.fn(),
  resize: vi.fn(),
  setOption: vi.fn(),
};
const echarts = { init: vi.fn(() => chart) };

vi.mock('@/lib/echarts.js', async (importOriginal) => ({
  ...(await importOriginal()),
  loadECharts: vi.fn(async () => echarts),
}));

import StorageTrendChart from '@/components/dashboard/StorageTrendChart.vue';
import {
  buildStorageTrendOption,
  insertThresholdCrossings,
} from '@/utils/storage-trend-chart.js';

const palette = {
  normal: '#446AEE',
  important: '#D69B1E',
  serious: '#EF5923',
  emergency: '#D3372F',
  grid: '#E2E8F0',
  axis: '#64748B',
  surface: '#FFFFFF',
  series: ['#446AEE', '#0EA5B7'],
};
const meta = {
  quota_basis: 'soft',
  rule_source: 'group',
  thresholds: { important: 80, serious: 90, emergency: 95 },
  quota_limit_gb: 100,
  ratio_indicator: 'soft_use_ratio',
};

describe('storage trend option', () => {
  it('inserts exact synthetic crossing points for every crossed threshold', () => {
    const result = insertThresholdCrossings([
      ['2026-07-17T10:00:00', 78],
      ['2026-07-17T10:10:00', 97],
    ], [80, 90, 95]);

    expect(result.map((point) => point.value[1])).toEqual([78, 80, 90, 95, 97]);
    expect(result.slice(1, -1).every((point) => point.synthetic)).toBe(true);
  });

  it('builds the approved 0-100 percentage axis, dotted grid, labels above lines, and four colors', () => {
    const option = buildStorageTrendOption({
      series: [{ name: '/home/alice', data: [['2026-07-17T10:00:00', 78], ['2026-07-17T10:10:00', 97]] }],
      indicator: 'alert_ratio',
      trendMeta: meta,
      palette,
    });

    expect(option.yAxis).toMatchObject({ min: 0, max: 100, interval: 10 });
    expect(option.yAxis.splitLine.lineStyle.type).toBe('dotted');
    expect(option.visualMap.pieces.map((piece) => piece.color)).toEqual([
      palette.normal,
      palette.important,
      palette.serious,
      palette.emergency,
    ]);
    expect(option.series[0].lineStyle.color).toBeUndefined();
    expect(option.series[0].areaStyle).toBeUndefined();
    expect(option.series[0].markPoint).toBeUndefined();
    expect(option.series[0].markLine.data.map((line) => line.label.formatter)).toEqual([
      '重要 80%',
      '严重 90%',
      '紧急 95%',
    ]);
    expect(option.series[0].markLine.data.every((line) => line.label.offset[1] < 0)).toBe(true);
    expect(option.tooltip.formatter([{
      axisValue: '2026-07-17T10:10:00',
      data: { value: ['2026-07-17T10:10:00', 93.2] },
      marker: '●',
      seriesName: '/home/alice',
    }])).toContain('当前等级：严重 · 软限额 · 项目组规则');
  });

  it('maps capacity thresholds to the effective quota and keeps multi-capacity uncluttered', () => {
    const single = buildStorageTrendOption({
      series: [{ name: 'volume-a', data: [['2026-07-17T10:00:00', 81]] }],
      indicator: 'used',
      trendMeta: { ...meta, quota_limit_gb: 200 },
      palette,
    });
    expect(single.series[0].markLine.data.map((line) => line.yAxis)).toEqual([160, 180, 190]);

    const multiple = buildStorageTrendOption({
      series: [
        { name: 'volume-a', data: [['2026-07-17T10:00:00', 81]] },
        { name: 'volume-b', data: [['2026-07-17T10:00:00', 60]] },
      ],
      indicator: 'used',
      trendMeta: meta,
      palette,
    });
    expect(multiple.visualMap).toBeUndefined();
    expect(multiple.series.every((item) => item.markLine === undefined)).toBe(true);
    expect(multiple.series.map((item) => item.lineStyle.color)).toEqual(palette.series);
  });
});

describe('StorageTrendChart', () => {
  const originalResizeObserver = global.ResizeObserver;
  let resizeCallback;
  let disconnect;

  beforeEach(() => {
    vi.clearAllMocks();
    disconnect = vi.fn();
    global.ResizeObserver = class ResizeObserver {
      constructor(callback) { resizeCallback = callback; }
      observe() {}
      disconnect() { disconnect(); }
    };
  });

  afterEach(() => {
    global.ResizeObserver = originalResizeObserver;
  });

  it('renders, resizes, updates, and disposes the shared chart', async () => {
    const wrapper = mount(StorageTrendChart, {
      props: {
        series: [{ name: '/home/alice', data: [['2026-07-17T10:00:00', 81]] }],
        indicator: 'alert_ratio',
        trendMeta: meta,
        ariaLabel: '用户目录使用率趋势',
      },
    });
    await flushPromises();

    expect(echarts.init).toHaveBeenCalledTimes(1);
    expect(chart.setOption).toHaveBeenCalledTimes(1);
    expect(wrapper.attributes('aria-label')).toBe('用户目录使用率趋势');

    resizeCallback();
    expect(chart.resize).toHaveBeenCalledTimes(1);

    await wrapper.setProps({ indicator: 'used' });
    await flushPromises();
    expect(chart.setOption).toHaveBeenCalledTimes(2);

    wrapper.unmount();
    expect(disconnect).toHaveBeenCalledTimes(1);
    expect(chart.dispose).toHaveBeenCalledTimes(1);
  });
});
