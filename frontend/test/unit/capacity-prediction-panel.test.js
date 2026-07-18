import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({
  fetchPrediction: vi.fn(),
  fetchPlans: vi.fn(),
  fetchRelatedIncidents: vi.fn(),
  createPlan: vi.fn(),
}));

vi.mock('@/api/capacity-prediction-api.js', () => ({ default: api }));
vi.mock('@/lib/echarts.js', () => ({
  getChartColors: () => ['#1', '#2', '#3', '#4'],
  loadEcharts: vi.fn(),
}));

import CapacityPredictionPanel from '@/pages/capacity-prediction/CapacityPredictionPanel.vue';

const mountPanel = (props = {}) => shallowMount(CapacityPredictionPanel, {
  props: { assetType: 'group', assetId: 7, visible: true, ...props },
  global: {
    directives: { loading: () => {} },
    stubs: {
      ElAlert: { props: ['title'], template: '<div data-test="error">{{ title }}</div>' },
      ElEmpty: { props: ['description'], template: '<div data-test="empty">{{ description }}</div>' },
    },
  },
});

describe('CapacityPredictionPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.fetchPlans.mockResolvedValue([]);
    api.fetchRelatedIncidents.mockResolvedValue([]);
  });

  it('renders an empty state when the resource has no forecast yet', async () => {
    api.fetchPrediction.mockRejectedValue({ response: { status: 404 } });

    const wrapper = mountPanel();
    await flushPromises();

    expect(wrapper.find('[data-test="empty"]').text()).toContain('暂无可用容量预测');
    expect(wrapper.find('[data-test="error"]').exists()).toBe(false);
  });

  it('renders an error state for non-404 failures', async () => {
    api.fetchPrediction.mockRejectedValue({ response: { status: 503 } });

    const wrapper = mountPanel();
    await flushPromises();

    expect(wrapper.find('[data-test="error"]').text()).toContain('容量预测暂不可用');
    expect(wrapper.find('[data-test="empty"]').exists()).toBe(false);
  });

  it('does not load prediction data before the lazy panel becomes visible', async () => {
    mountPanel({ visible: false });
    await flushPromises();

    expect(api.fetchPrediction).not.toHaveBeenCalled();
    expect(api.fetchPlans).not.toHaveBeenCalled();
    expect(api.fetchRelatedIncidents).not.toHaveBeenCalled();
  });
});
