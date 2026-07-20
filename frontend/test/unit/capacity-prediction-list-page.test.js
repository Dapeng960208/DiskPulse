import { h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CapacityPredictionListPage from '@/pages/capacity-prediction/CapacityPredictionListPage.vue';

const { capacityPredictionApi } = vi.hoisted(() => ({
  capacityPredictionApi: { visibility: vi.fn(), fetchPredictions: vi.fn() },
}));

vi.mock('@/api/capacity-prediction-api.js', () => ({ default: capacityPredictionApi }));

let tableRow = {};

const DataTable = {
  name: 'DataTable',
  props: ['data', 'loading', 'error', 'pagination'],
  template: '<section>{{ JSON.stringify(data) }}<slot /></section>',
};

const ElTableColumn = {
  name: 'ElTableColumn',
  props: ['label', 'prop'],
  setup(props, { slots }) {
    return () => h('div', { 'data-column': props.label }, [
      slots.default
        ? slots.default({ row: tableRow })
        : (props.prop ? tableRow[props.prop] : ''),
    ]);
  },
};

const mountPage = () => shallowMount(CapacityPredictionListPage, {
  global: {
    stubs: {
      DataTable,
      ElEmpty: { name: 'ElEmpty', props: ['description'], template: '<div>{{ description }}</div>' },
      ElTableColumn,
      ElTag: { name: 'ElTag', template: '<span><slot /></span>' },
      AccessibleResourceLink: { name: 'AccessibleResourceLink', template: '<a><slot /></a>' },
    },
  },
});

describe('CapacityPredictionListPage', () => {
  beforeEach(() => {
    tableRow = {};
    capacityPredictionApi.visibility.mockResolvedValue({ visible: true });
    capacityPredictionApi.fetchPredictions.mockResolvedValue({
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
    expect(capacityPredictionApi.fetchPredictions).toHaveBeenCalledWith({ page: 1, size: 20 });
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

    expect(capacityPredictionApi.fetchPredictions).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain('容量预测未启用或当前账号无访问权限');
  });

  it('links only the final-prediction resource types to their prediction details', () => {
    const wrapper = mountPage();

    expect(wrapper.vm.detailTarget({ asset_type: 'group', asset_id: '1' }))
      .toEqual({ name: 'GroupCapacityPrediction', params: { id: 1 } });
    expect(wrapper.vm.detailTarget({ asset_type: 'storage_usage', asset_id: '2' }))
      .toEqual({ name: 'UsageCapacityPrediction', params: { id: 2 } });
    expect(wrapper.vm.detailTarget({ asset_type: 'storage_cluster', asset_id: '1' }))
      .toBeNull();
    expect(wrapper.vm.detailTarget({ asset_type: 'volume', asset_id: '2' }))
      .toBeNull();
    expect(wrapper.vm.detailTarget({ asset_type: 'qtree', asset_id: '3' }))
      .toBeNull();
  });

  it('requests the selected server-side page from the final-prediction endpoint', async () => {
    const wrapper = mountPage();
    await flushPromises();

    wrapper.findComponent(DataTable).vm.$emit('update:pagination', { page: 3, pageSize: 50 });
    await flushPromises();

    expect(capacityPredictionApi.fetchPredictions).toHaveBeenLastCalledWith({ page: 3, size: 50 });
  });

  it('prefers the candidate model version and falls back to the algorithm version', async () => {
    tableRow = {
      input_quality: { candidate_version: 'capacity-ai-candidate-v3' },
      algorithm_version: 'capacity-ai-v2',
    };
    const candidateWrapper = mountPage();
    await flushPromises();
    expect(candidateWrapper.find('[data-column="模型版本"]').text()).toBe('capacity-ai-candidate-v3');

    tableRow = { input_quality: {}, algorithm_version: 'capacity-ai-v2' };
    const fallbackWrapper = mountPage();
    await flushPromises();
    expect(fallbackWrapper.find('[data-column="模型版本"]').text()).toBe('capacity-ai-v2');
  });

  it('keeps the newest page state when deferred requests finish out of order', async () => {
    const requests = [];
    capacityPredictionApi.fetchPredictions.mockImplementation((params) => new Promise((resolve, reject) => {
      requests.push({ params, resolve, reject });
    }));

    const wrapper = mountPage();
    await flushPromises();
    wrapper.findComponent(DataTable).vm.$emit('update:pagination', { page: 2, pageSize: 20 });
    await flushPromises();
    wrapper.findComponent(DataTable).vm.$emit('update:pagination', { page: 3, pageSize: 20 });
    await flushPromises();

    expect(requests.map(({ params }) => params)).toEqual([
      { page: 1, size: 20 },
      { page: 2, size: 20 },
      { page: 3, size: 20 },
    ]);
    const latest = { id: 'latest-page' };
    requests[2].resolve({ total: 1, content: [latest] });
    await flushPromises();
    expect(wrapper.vm.predictions).toEqual([latest]);
    expect(wrapper.vm.pagination.total).toBe(1);
    expect(wrapper.vm.loading).toBe(false);
    expect(wrapper.vm.error).toBe('');

    requests[0].resolve({ total: 1, content: [{ id: 'stale-first' }] });
    requests[1].reject(new Error('stale second request'));
    await flushPromises();
    expect(wrapper.vm.predictions).toEqual([latest]);
    expect(wrapper.vm.pagination.total).toBe(1);
    expect(wrapper.vm.loading).toBe(false);
    expect(wrapper.vm.error).toBe('');
  });
});
