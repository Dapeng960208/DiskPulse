import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CapacityPredictionListPage from '@/pages/capacity-prediction/CapacityPredictionListPage.vue';

const { capacityPredictionApi, incidentApi } = vi.hoisted(() => ({
  capacityPredictionApi: { visibility: vi.fn() },
  incidentApi: { fetchForecasts: vi.fn() },
}));

vi.mock('@/api/capacity-prediction-api.js', () => ({ default: capacityPredictionApi }));
vi.mock('@/api/incident-api.js', () => ({ default: incidentApi }));

const DataTable = {
  name: 'DataTable',
  props: ['data', 'loading', 'error', 'pagination'],
  template: '<section>{{ JSON.stringify(data) }}<slot /></section>',
};

const mountPage = () => shallowMount(CapacityPredictionListPage, {
  global: {
    stubs: {
      DataTable,
      ElEmpty: { name: 'ElEmpty', props: ['description'], template: '<div>{{ description }}</div>' },
      ElTableColumn: { name: 'ElTableColumn', template: '<div />' },
      ElTag: { name: 'ElTag', template: '<span><slot /></span>' },
      AccessibleResourceLink: { name: 'AccessibleResourceLink', template: '<a><slot /></a>' },
    },
  },
});

describe('CapacityPredictionListPage', () => {
  beforeEach(() => {
    capacityPredictionApi.visibility.mockResolvedValue({ visible: true });
    incidentApi.fetchForecasts.mockResolvedValue({
      total: 1,
      content: [{
        id: 91,
        asset_type: 'storage_usage',
        asset_id: '234',
        display_name: '/data/project/alice',
        exhaustion_dates: { p50: '2026-10-01' },
        algorithm_version: 'capacity-ai-v2',
        input_quality: { prediction_source: 'ai_candidate' },
        created_at: '2026-07-19T08:00:00Z',
      }],
    });
  });

  it('loads the latest accessible prediction results from a standalone page', async () => {
    const wrapper = mountPage();
    await flushPromises();

    expect(capacityPredictionApi.visibility).toHaveBeenCalledTimes(1);
    expect(incidentApi.fetchForecasts).toHaveBeenCalledWith({ page: 1, size: 20 });
    expect(wrapper.findComponent(DataTable).props('data')).toHaveLength(1);
    expect(wrapper.vm.detailTarget(wrapper.vm.predictions[0])).toEqual({
      name: 'UsageCapacityPrediction',
      params: { id: 234 },
    });
  });

  it('does not request predictions when the feature is not published to the user', async () => {
    capacityPredictionApi.visibility.mockResolvedValueOnce({ visible: false });
    const wrapper = mountPage();
    await flushPromises();

    expect(incidentApi.fetchForecasts).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain('容量预测未启用或当前账号无访问权限');
  });
});
