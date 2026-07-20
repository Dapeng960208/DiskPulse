import { flushPromises, shallowMount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';

const chartMock = vi.hoisted(() => {
  const instances = [];
  const init = vi.fn((dom) => {
    const handlers = {};
    const instance = {
      dom,
      handlers,
      dispose: vi.fn(),
      hideLoading: vi.fn(),
      on: vi.fn((event, handler) => {
        handlers[event] = handler;
      }),
      resize: vi.fn(),
      setOption: vi.fn(),
      showLoading: vi.fn(),
    };
    instances.push(instance);
    return instance;
  });

  return { init, instances };
});

vi.mock('echarts', () => ({
  format: {
    addCommas: (value) => String(value),
    encodeHTML: (value) => String(value),
  },
  graphic: { LinearGradient: class LinearGradient {} },
  init: chartMock.init,
}));

import AnimatedTextChart from '@/common/charts/AnimatedTextChart.vue';
import BarStackChart from '@/common/charts/BarStackChart.vue';
import DiskUsage from '@/common/charts/DiskUsage.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import PieCharts from '@/common/charts/PieCharts.vue';
import StoragePieAndLineCharts from '@/common/charts/StoragePieAndLineCharts.vue';

vi.spyOn(console, 'log').mockImplementation(() => undefined);

const mountedWrappers = [];

const mountChart = async (component, props) => {
  const wrapper = shallowMount(component, {
    attachTo: document.body,
    props,
  });
  mountedWrappers.push(wrapper);
  await flushPromises();
  await nextTick();
  return wrapper;
};

const setDimensions = (wrapper) => {
  Object.defineProperty(wrapper.element, 'clientWidth', { configurable: true, value: 320 });
  Object.defineProperty(wrapper.element, 'clientHeight', { configurable: true, value: 240 });
};

const latestChart = () => chartMock.instances.at(-1);
const latestOption = () => latestChart().setOption.mock.calls[0][0];

beforeEach(() => {
  chartMock.init.mockClear();
  chartMock.instances.length = 0;
});

afterEach(() => {
  mountedWrappers.splice(0).forEach((wrapper) => wrapper.unmount());
});

describe('chart coverage gaps', () => {
  it('renders DiskUsage data, formats its tooltip, resizes, and re-renders', async () => {
    const empty = await mountChart(DiskUsage, { data: [] });
    expect(chartMock.init).not.toHaveBeenCalled();
    empty.unmount();

    const wrapper = shallowMount(DiskUsage, {
      attachTo: document.body,
      props: {
        data: [{ name: 'root', used: 1, limit: 2, used_ratio: 50 }],
        label: '容量',
        title: '磁盘使用率',
      },
    });
    mountedWrappers.push(wrapper);
    setDimensions(wrapper);
    await flushPromises();
    await nextTick();

    const instance = latestChart();
    const option = latestOption();
    expect(option.series[0].name).toBe('容量');
    expect(option.series[0].visibleMin).toBe(0);
    expect(option.series[0].levels).toHaveLength(3);
    expect(option.tooltip.formatter({
      data: { limit: 2048, used: 1024, used_ratio: 50 },
      treePathInfo: [{ name: 'root' }, { name: 'project' }, { name: 'user' }],
    })).toContain('project/user');

    window.dispatchEvent(new Event('resize'));
    expect(instance.resize).toHaveBeenCalledTimes(1);

    await wrapper.setProps({ data: [{ name: 'root', used: 2, limit: 4, used_ratio: 50 }] });
    await flushPromises();
    await nextTick();
    expect(instance.dispose).toHaveBeenCalledTimes(1);
    expect(chartMock.init).toHaveBeenCalledTimes(2);
  });

  it('builds BarStackChart series, labels, tooltips, and watcher updates', async () => {
    const wrapper = await mountChart(BarStackChart, {
      categories: ['short', 'a category name longer than ten'],
      data: [[1, 0], [3, 0]],
      seriesMap: { mapped: '已映射' },
      seriesNames: ['raw', 'mapped'],
      unit: 'G',
    });

    const instance = latestChart();
    const option = latestOption();
    expect(option.title.bottom).toBe(8);
    expect(option.grid.bottom).toBe(120);
    expect(option.series.map((series) => series.name)).toEqual(['raw', '已映射']);
    expect(option.series[0].data).toEqual([1, 0]);
    expect(option.series[0].label.formatter({ value: 1.6 })).toBe('2G');
    expect(option.xAxis.axisLabel.formatter('short')).toBe('short');
    expect(option.xAxis.axisLabel.formatter('a category name longer than ten')).toBe('a category...');
    expect(option.xAxis.axisLabel.width).toBe(100);
    expect(option.tooltip.formatter([
      { axisValue: 'short', marker: '*', seriesName: 'raw', value: 1 },
      { marker: '+', seriesName: 'mapped', value: 3 },
    ])).toContain('raw: 1G');

    window.dispatchEvent(new Event('resize'));
    expect(instance.resize).toHaveBeenCalledTimes(1);

    await wrapper.setProps({ categories: ['updated'], data: [[2], [3]], seriesNames: ['raw', 'mapped'] });
    await flushPromises();
    expect(instance.dispose).toHaveBeenCalled();
    expect(chartMock.init).toHaveBeenCalled();
  });

  it('renders AnimatedTextChart and responds to props and resize', async () => {
    const wrapper = await mountChart(AnimatedTextChart, {
      animationDuration: 500,
      fillColor: '#fff',
      fontSize: 24,
      fontWeight: 'normal',
      strokeColor: '#000',
      text: 'NO DATA',
    });
    const instance = latestChart();
    const element = latestOption().graphic.elements[0];
    expect(element.style).toMatchObject({ fontSize: 24, text: 'NO DATA', stroke: '#000' });
    expect(element.keyframeAnimation.duration).toBe(500);

    window.dispatchEvent(new Event('resize'));
    expect(instance.resize).toHaveBeenCalledTimes(1);
    await wrapper.setProps({ text: 'EMPTY', width: '400px', height: '200px' });
    await flushPromises();
    expect(instance.dispose).toHaveBeenCalled();
  });

  it('renders LoadingCharts and handles prop changes and resize', async () => {
    const wrapper = await mountChart(LoadingCharts, { height: '240px', width: '320px' });
    const instance = latestChart();
    expect(latestOption().graphic.elements[0].children).toHaveLength(7);

    window.dispatchEvent(new Event('resize'));
    expect(instance.resize).toHaveBeenCalledTimes(1);
    await wrapper.setProps({ width: '400px' });
    await flushPromises();
    expect(instance.dispose).toHaveBeenCalled();
    expect(latestChart().setOption).toHaveBeenCalledTimes(1);
  });

  it('renders PieCharts through empty and populated data paths', async () => {
    const empty = await mountChart(PieCharts, { data: [] });
    expect(chartMock.init).not.toHaveBeenCalled();
    empty.unmount();

    const wrapper = await mountChart(PieCharts, {
      data: [{ name: '项目 A', value: 10 }],
      title: '容量分布',
    });
    const instance = latestChart();
    expect(latestOption().series[0].name).toBe('容量分布');
    window.dispatchEvent(new Event('resize'));
    expect(instance.resize).toHaveBeenCalledTimes(1);
    await wrapper.setProps({ data: [{ name: '项目 B', value: 20 }], title: '更新分布' });
    await flushPromises();
    expect(instance.dispose).toHaveBeenCalled();
  });

  it('renders StoragePieAndLineCharts and handles axis pointer events', async () => {
    const empty = await mountChart(StoragePieAndLineCharts, { data: [] });
    expect(chartMock.init).not.toHaveBeenCalled();
    empty.unmount();

    const wrapper = await mountChart(StoragePieAndLineCharts, {
      data: [
        ['project', 'Jan', 'Feb'],
        ['项目 A', 1, 2],
        ['项目 B', 3, 4],
      ],
      title: '存储趋势',
      yAxisUnit: 'TB',
    });
    const instance = latestChart();
    expect(latestOption().series).toHaveLength(3);
    instance.handlers.updateAxisPointer({ axesInfo: [] });
    expect(instance.setOption).toHaveBeenCalledTimes(1);
    instance.handlers.updateAxisPointer({ axesInfo: [{ value: 1 }] });
    expect(instance.setOption).toHaveBeenCalledTimes(2);
    expect(instance.setOption.mock.calls[1][0].series.encode.value).toBe(2);

    window.dispatchEvent(new Event('resize'));
    expect(instance.resize).toHaveBeenCalledTimes(1);
    await wrapper.setProps({ title: '更新趋势' });
    expect(instance.dispose).toHaveBeenCalledTimes(1);
  });
});
