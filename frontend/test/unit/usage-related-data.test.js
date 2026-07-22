import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { alertApi, breadcrumbs, capacityPredictionApi, storageUsageApi } = vi.hoisted(() => ({
  alertApi: { fetch: vi.fn() },
  breadcrumbs: { setDetailBreadcrumb: vi.fn() },
  capacityPredictionApi: {
    visibility: vi.fn(),
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
vi.mock('@/stores/breadcrumbs', () => ({ useBreadcrumbs: () => breadcrumbs }));
vi.mock('@/components/form/QuotaAdjustmentDialog.vue', () => ({
  default: { name: 'QuotaAdjustmentDialog', template: '<div />' },
}));
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
  setup(props) {
    return () => h('div', [props.error, JSON.stringify(props.data)]);
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
    vi.clearAllMocks();
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
    capacityPredictionApi.visibility.mockResolvedValue({ visible: true });
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

  it('exposes quota history, exhaustion risk, and incidents without a duplicate alert tab', async () => {
    const wrapper = mountPage();
    await flushPromises();

    expect(wrapper.text()).toContain('配额历史');
    expect(wrapper.text()).toContain('耗尽风险');
    expect(wrapper.text()).toContain('关联事件');
    expect(wrapper.find('[data-tab="alerts"]').exists()).toBe(false);
    expect(storageUsageApi.fetchById).toHaveBeenCalledWith(234, undefined, expect.objectContaining({ errorHandlerDisabled: true }));
    expect(capacityPredictionApi.visibility).toHaveBeenCalledTimes(1);
    expect(storageUsageApi.quotaHistory).not.toHaveBeenCalled();

    wrapper.vm.activeTab = 'quota-history';
    await flushPromises();
    expect(storageUsageApi.quotaHistory).toHaveBeenCalledWith(234, expect.objectContaining({ errorHandlerDisabled: true }));

    wrapper.vm.activeTab = 'incidents';
    await flushPromises();
    expect(capacityPredictionApi.fetchRelatedIncidents).toHaveBeenCalledWith('storage_usage', 234, expect.objectContaining({ errorHandlerDisabled: true }));

    wrapper.vm.activeTab = 'alerts';
    await flushPromises();
    expect(alertApi.fetch).not.toHaveBeenCalled();
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

  it('hides the exhaustion-risk tab when global visibility is disabled', async () => {
    capacityPredictionApi.visibility.mockResolvedValueOnce({ visible: false });
    const wrapper = mountPage();
    await flushPromises();

    expect(wrapper.text()).not.toContain('耗尽风险');
  });

  it('treats a risk visibility 403 as unavailable instead of a load failure', async () => {
    capacityPredictionApi.visibility.mockRejectedValueOnce({ response: { status: 403 } });
    const wrapper = mountPage();
    await flushPromises();

    expect(wrapper.text()).not.toContain('耗尽风险');
  });
});
