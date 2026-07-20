import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ElMessage } from 'element-plus';

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
    api.createPlan.mockResolvedValue({ id: 1 });
    vi.spyOn(ElMessage, 'success').mockImplementation(() => {});
    vi.spyOn(ElMessage, 'error').mockImplementation(() => {});
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

  it('renders forecast values from the response capacity map and keeps the declared curve unit', async () => {
    api.fetchPrediction.mockResolvedValue({
      data_unit: 'GB',
      curve: [],
      exhaustion_dates: {}, input_quality: {}, algorithm_version: 'capacity-ai-v2',
    });
    const wrapper = mountPanel();
    await flushPromises();

    expect(wrapper.vm.curveUnit).toBe('GB');
    expect(wrapper.vm.formatCurveCapacity({
      p50: 2048,
      capacity: { p50: { value: 2, unit: 'TB' } },
    }, 'p50')).toBe('2 TB');
  });

  it('creates a resource-scoped capacity plan and reloads the panel', async () => {
    api.fetchPrediction.mockRejectedValue({ response: { status: 404 } });
    const wrapper = mountPanel({ canManagePlans: true });
    await flushPromises();

    wrapper.vm.openPlanDialog();
    wrapper.vm.planForm.effectiveAt = new Date('2026-08-01T00:00:00Z');
    wrapper.vm.planForm.capacityDelta = 2048;
    wrapper.vm.planForm.reason = '  approved expansion  ';
    await wrapper.vm.createPlan();

    expect(api.createPlan).toHaveBeenCalledWith('group', 7, {
      effective_at: '2026-08-01T00:00:00.000Z',
      capacity_delta: 2048,
      reason: 'approved expansion',
    });
    expect(ElMessage.success).toHaveBeenCalledWith('容量计划已保存');
    expect(api.fetchPrediction).toHaveBeenCalledTimes(2);
  });

  it('keeps the plan dialog open and reports a failed save', async () => {
    api.fetchPrediction.mockRejectedValue({ response: { status: 404 } });
    api.createPlan.mockRejectedValue(new Error('forbidden'));
    const wrapper = mountPanel({ canManagePlans: true });
    await flushPromises();

    wrapper.vm.openPlanDialog();
    wrapper.vm.planForm.capacityDelta = 1;
    wrapper.vm.planForm.reason = 'approved cleanup';
    await wrapper.vm.createPlan();

    expect(ElMessage.error).toHaveBeenCalledWith('保存容量计划失败，请确认项目管理员权限后重试');
    expect(wrapper.vm.planDialogVisible).toBe(true);
  });

  it('updates dialog visibility through the v-model contract', async () => {
    api.fetchPrediction.mockRejectedValue({ response: { status: 404 } });
    const wrapper = mountPanel({ canManagePlans: true });
    await flushPromises();

    wrapper.vm.openPlanDialog();
    await wrapper.findComponent({ name: 'ElDialog' }).vm.$emit('update:modelValue', false);

    expect(wrapper.vm.planDialogVisible).toBe(false);
  });
});
