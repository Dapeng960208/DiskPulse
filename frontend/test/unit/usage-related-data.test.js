import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { alertApi, capacityPredictionApi, storageUsageApi } = vi.hoisted(() => ({
  alertApi: { fetch: vi.fn() },
  capacityPredictionApi: {
    fetchPrediction: vi.fn(),
    fetchRelatedIncidents: vi.fn(),
  },
  storageUsageApi: {
    fetchById: vi.fn(),
    quotaHistory: vi.fn(),
  },
}));

vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'UsagesDetail', params: { id: '234' } }),
}));
vi.mock('@/api/alert-api.js', () => ({ default: alertApi }));
vi.mock('@/api/capacity-prediction-api.js', () => ({ default: capacityPredictionApi }));
vi.mock('@/api/storage-usage-api.js', () => ({ default: storageUsageApi }));
vi.mock('@/pages/common/RealTimePage.vue', () => ({
  default: { name: 'RealTimePage', template: '<div>容量趋势</div>' },
}));

import UsageDetailPage from '@/pages/usage/UsageDetailPage.vue';

const passthrough = (name, tag = 'div') => defineComponent({
  name,
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    return () => h(tag, attrs, slots.default?.());
  },
});
const TabPane = defineComponent({
  name: 'ElTabPane',
  props: { label: String, name: String },
  setup(props, { slots }) {
    return () => h('section', { 'data-tab': props.name }, [props.label, ...(slots.default?.() || [])]);
  },
});
const DataTable = defineComponent({
  name: 'DataTable',
  props: { data: { type: Array, default: () => [] }, error: String },
  setup(props, { slots }) {
    return () => h('div', [props.error, JSON.stringify(props.data), ...(slots.default?.() || [])]);
  },
});

const mountPage = () => shallowMount(UsageDetailPage, {
  global: {
    stubs: {
      ElTabs: passthrough('ElTabs'),
      ElTabPane: TabPane,
      ElDescriptions: passthrough('ElDescriptions'),
      ElDescriptionsItem: passthrough('ElDescriptionsItem'),
      ElEmpty: { name: 'ElEmpty', props: ['description'], template: '<div>{{ description }}</div>' },
      ElTag: passthrough('ElTag', 'span'),
      ElTableColumn: passthrough('ElTableColumn'),
      DataTable,
      RealTimePage: passthrough('RealTimePage'),
    },
    directives: { loading: () => undefined },
  },
});

describe('user-directory related data', () => {
  beforeEach(() => {
    storageUsageApi.fetchById.mockResolvedValue({
      id: 234,
      linux_path: '/data/project/alice',
      capabilities: { adjust_quota: true },
    });
    storageUsageApi.quotaHistory.mockResolvedValue([{
      id: 'audit-1',
      occurred_at: '2026-07-19T08:00:00Z',
      action: 'quota.adjust',
      outcome: 'success',
      before_summary: { hard_limit: 100 },
      after_summary: { hard_limit: 120 },
      metadata: { change_reason: '项目扩容' },
    }]);
    capacityPredictionApi.fetchPrediction.mockResolvedValue({
      id: 91,
      algorithm_version: 'capacity-ai-v2',
      exhaustion_dates: { p50: '2026-10-01' },
      input_quality: { status: 'ready', coverage_ratio: 0.98, prediction_source: 'ai_candidate' },
      curve: [{ observed_at: '2026-07-20', p50: 88 }],
    });
    capacityPredictionApi.fetchRelatedIncidents.mockResolvedValue([{
      id: 301,
      category: 'capacity_pressure',
      severity: 'warning',
      status: 'open',
      updated_at: '2026-07-19T08:00:00Z',
    }]);
    alertApi.fetch.mockResolvedValue({
      total: 1,
      content: [{ id: 7, alert_level: 'important', description: '容量超过阈值' }],
    });
  });

  it('exposes quota history, final prediction, incidents, and alerts as lazy detail tabs', async () => {
    const wrapper = mountPage();
    await flushPromises();

    expect(wrapper.text()).toContain('配额历史');
    expect(wrapper.text()).toContain('容量预测最终结果');
    expect(wrapper.text()).toContain('关联事件');
    expect(wrapper.text()).toContain('告警');
    expect(storageUsageApi.fetchById).toHaveBeenCalledWith(234, undefined, expect.objectContaining({ errorHandlerDisabled: true }));
    expect(storageUsageApi.quotaHistory).not.toHaveBeenCalled();

    wrapper.vm.activeTab = 'quota-history';
    await flushPromises();
    expect(storageUsageApi.quotaHistory).toHaveBeenCalledWith(234, expect.objectContaining({ errorHandlerDisabled: true }));

    wrapper.vm.activeTab = 'prediction';
    await flushPromises();
    expect(capacityPredictionApi.fetchPrediction).toHaveBeenCalledWith('storage_usage', 234, expect.objectContaining({ errorHandlerDisabled: true }));

    wrapper.vm.activeTab = 'incidents';
    await flushPromises();
    expect(capacityPredictionApi.fetchRelatedIncidents).toHaveBeenCalledWith('storage_usage', 234, expect.objectContaining({ errorHandlerDisabled: true }));

    wrapper.vm.activeTab = 'alerts';
    await flushPromises();
    expect(alertApi.fetch).toHaveBeenCalledWith({
      related_type: 'StorageUsage',
      related_id: 234,
      page: 1,
      size: 20,
    });
  });

  it('does not request quota history when the current user lacks its narrower permission', async () => {
    storageUsageApi.fetchById.mockResolvedValueOnce({ id: 234, capabilities: { adjust_quota: false } });
    const wrapper = mountPage();
    await flushPromises();

    wrapper.vm.activeTab = 'quota-history';
    await flushPromises();

    expect(storageUsageApi.quotaHistory).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain('当前账号无权查看配额历史');
  });

  it('keeps incidents and alerts available when no final prediction exists', async () => {
    capacityPredictionApi.fetchPrediction.mockRejectedValueOnce({ response: { status: 404 } });
    const wrapper = mountPage();
    await flushPromises();

    wrapper.vm.activeTab = 'prediction';
    await flushPromises();
    expect(wrapper.text()).toContain('暂无容量预测最终结果');

    wrapper.vm.activeTab = 'incidents';
    await flushPromises();
    wrapper.vm.activeTab = 'alerts';
    await flushPromises();

    expect(capacityPredictionApi.fetchRelatedIncidents).toHaveBeenCalledTimes(1);
    expect(alertApi.fetch).toHaveBeenCalledTimes(1);
  });
});
