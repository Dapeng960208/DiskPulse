import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

const aggregateApi = vi.hoisted(() => ({
  fetchAggregateTrees: vi.fn(() => Promise.resolve({ data: [{ name: 'vol-a' }] })),
}));

vi.mock('@/api/aggregate-api.js', () => ({ default: aggregateApi }));
vi.mock('@/components/form/StorageClusterSelect.vue', () => ({
  default: {
    name: 'StorageClusterSelect',
    props: {
      modelValue: { type: Number, default: null },
      clearable: Boolean,
    },
    emits: ['update:modelValue'],
    template: '<select />',
  },
}));
vi.mock('@/common/charts/DiskUsage.vue', () => ({ default: { name: 'DiskUsage', template: '<div />' } }));
vi.mock('@/common/charts/LoadingCharts.vue', () => ({ default: { name: 'LoadingCharts', template: '<div />' } }));
vi.mock('@/common/charts/AnimatedTextChart.vue', () => ({ default: { name: 'AnimatedTextChart', template: '<div />' } }));

describe('AdminDashboard storage cluster filter', () => {
  it('reloads the storage tree for the selected cluster', async () => {
    const { default: AdminDashboard } = await import('@/pages/admin/dashboard/DashboardPage.vue');
    const wrapper = shallowMount(AdminDashboard, {
      attachTo: document.body,
      global: {
        stubs: {
          ElCard: { template: '<section><slot /></section>' },
        },
      },
    });
    await flushPromises();

    expect(aggregateApi.fetchAggregateTrees).toHaveBeenNthCalledWith(1, {
      storage_cluster_id: null,
    });

    const select = wrapper.findComponent({ name: 'StorageClusterSelect' });
    expect(select.props('clearable')).toBe(true);
    await select.vm.$emit('update:modelValue', 2);
    await flushPromises();

    expect(aggregateApi.fetchAggregateTrees).toHaveBeenLastCalledWith({
      storage_cluster_id: 2,
    });
    wrapper.unmount();
  });
});
