import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { fetchGroup, setDetailBreadcrumb, visibilityMock } = vi.hoisted(() => ({
  fetchGroup: vi.fn(),
  setDetailBreadcrumb: vi.fn(),
  visibilityMock: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '234' } }),
}));

vi.mock('vue', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    defineAsyncComponent: () => ({
      name: 'CapacityExhaustionRiskPanel',
      props: ['assetType', 'assetId'],
      template: '<section data-testid="capacity-exhaustion-risk-panel">耗尽风险内容</section>',
    }),
  };
});

vi.mock('@/api/capacity-prediction-api.js', () => ({
  default: {
    visibility: visibilityMock,
  },
}));

vi.mock('@/api/group-api.js', () => ({
  default: { fetchById: fetchGroup },
}));

vi.mock('@/stores/breadcrumbs', () => ({
  useBreadcrumbs: () => ({ setDetailBreadcrumb }),
}));

vi.mock('@/api/storage-usage-api.js', () => ({
  default: {
    fetchById: vi.fn(() => Promise.resolve({ id: 234, capabilities: {} })),
    quotaHistory: vi.fn(() => Promise.resolve([])),
  },
}));

vi.mock('@/api/alert-api.js', () => ({
  default: { fetch: vi.fn(() => Promise.resolve({ content: [], total: 0 })) },
}));

vi.mock('@/pages/common/RealTimePage.vue', () => ({
  default: {
    name: 'RealTimePage',
    props: ['attributeId', 'apiType', 'label', 'showHeader'],
    template: '<main class="real-time-page-stub" :data-show-header="String(showHeader)"><slot name="extra-descriptions" :info="{}" /></main>',
  },
}));

import AggregateDetailPage from '@/pages/admin/aggregate/AggregateDetailPage.vue';
import GroupDetailPage from '@/pages/group/GroupDetailPage.vue';
import UsageDetailPage from '@/pages/usage/UsageDetailPage.vue';

const global = {
  stubs: {
    ElButton: {
      emits: ['click'],
      template: '<button type="button" @click="$emit(\'click\')"><slot /></button>',
    },
    ElDescriptionsItem: {
      template: '<div><slot /></div>',
    },
  },
};

describe('detail capacity prediction navigation', () => {
  beforeEach(() => {
    fetchGroup.mockReset();
    fetchGroup.mockResolvedValue({ id: 234, name: '研发组', project: { name: '项目 A' } });
    setDetailBreadcrumb.mockReset();
    visibilityMock.mockReset();
  });

  it('keeps realtime monitoring and embeds user-directory exhaustion risk', async () => {
    visibilityMock.mockResolvedValue({ visible: true });

    const wrapper = mount(UsageDetailPage, { global });
    await flushPromises();

    expect(wrapper.find('.real-time-page-stub').attributes('data-show-header')).toBe('false');
    expect(wrapper.find('.detail-monitor-page__actions').exists()).toBe(false);
    expect(wrapper.find('[data-testid="capacity-prediction-entry"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="capacity-exhaustion-risk-panel"]').exists()).toBe(true);
  });

  it('keeps realtime monitoring and embeds project-group exhaustion risk', async () => {
    const wrapper = mount(GroupDetailPage, { global });
    await flushPromises();

    expect(wrapper.find('.real-time-page-stub').attributes('data-show-header')).toBe('false');
    expect(wrapper.find('.detail-monitor-page__actions').exists()).toBe(false);
    expect(wrapper.find('[data-testid="capacity-prediction-entry"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="capacity-exhaustion-risk-panel"]').exists()).toBe(true);
  });

  it('hides the repeated monitoring title and subtitle in the capacity-pool detail page', () => {
    const wrapper = mount(AggregateDetailPage, { global });

    expect(wrapper.get('.real-time-page-stub').attributes('data-show-header')).toBe('false');
  });
});
