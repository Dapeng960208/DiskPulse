import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { accessMock } = vi.hoisted(() => ({
  accessMock: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '234' } }),
}));

vi.mock('vue', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    defineAsyncComponent: () => ({
      name: 'CapacityPredictionPanel',
      props: ['assetType', 'assetId', 'visible', 'canManagePlans'],
      template: '<section data-testid="capacity-prediction-panel">容量预测内容</section>',
    }),
  };
});

vi.mock('@/api/capacity-prediction-api.js', () => ({
  default: {
    access: accessMock,
  },
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
    accessMock.mockReset();
  });

  it('shows a user-directory capacity prediction entry only when access is enabled and opens it', async () => {
    accessMock.mockResolvedValue({ visible: true, can_manage_plans: false });

    const wrapper = mount(UsageDetailPage, { global });
    await flushPromises();

    expect(wrapper.find('.real-time-page-stub').attributes('data-show-header')).toBe('false');
    const entry = wrapper.get('[data-testid="capacity-prediction-entry"]');
    expect(entry.text()).toContain('容量预测');

    await entry.trigger('click');

    expect(wrapper.get('[data-testid="capacity-prediction-panel"]').text()).toContain('容量预测内容');
  });

  it('does not render the project-group capacity prediction entry when access is disabled', async () => {
    accessMock.mockResolvedValue({ visible: false, can_manage_plans: false });

    const wrapper = mount(GroupDetailPage, { global });
    await flushPromises();

    expect(wrapper.find('.real-time-page-stub').attributes('data-show-header')).toBe('false');
    expect(wrapper.find('[data-testid="capacity-prediction-entry"]').exists()).toBe(false);
  });

  it('hides the repeated monitoring title and subtitle in the capacity-pool detail page', () => {
    const wrapper = mount(AggregateDetailPage, { global });

    expect(wrapper.get('.real-time-page-stub').attributes('data-show-header')).toBe('false');
  });
});
