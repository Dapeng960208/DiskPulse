import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ClusterResourceListTab from '@/pages/admin/storage-cluster/components/ClusterResourceListTab.vue';

const aggregateApi = vi.hoisted(() => ({ fetch: vi.fn() }));
const volumeApi = vi.hoisted(() => ({ fetch: vi.fn() }));
const qtreeApi = vi.hoisted(() => ({ fetch: vi.fn() }));

vi.mock('@/api/aggregate-api.js', () => ({ default: aggregateApi }));
vi.mock('@/api/volume-api.js', () => ({ default: volumeApi }));
vi.mock('@/api/qtree-api.js', () => ({ default: qtreeApi }));

const DataTable = defineComponent({
  name: 'DataTable',
  props: {
    data: { type: Array, default: () => [] },
    loading: Boolean,
    pagination: { type: Object, default: () => ({}) },
  },
  emits: ['update:pagination'],
  setup(props, { slots }) {
    return () => h('section', { 'data-testid': 'cluster-resource-table' }, [
      JSON.stringify(props.data),
      ...(slots.default?.() || []),
    ]);
  },
});

const resourceCases = [
  ['aggregate', aggregateApi, { id: 1, name: 'pool-a' }],
  ['volume', volumeApi, { id: 2, name: 'volume-a' }],
  ['qtree', qtreeApi, { id: 3, name: 'qtree-a' }],
];

describe('ClusterResourceListTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    aggregateApi.fetch.mockResolvedValue({ content: [{ id: 1, name: 'pool-a' }], total: 1 });
    volumeApi.fetch.mockResolvedValue({ content: [{ id: 2, name: 'volume-a' }], total: 1 });
    qtreeApi.fetch.mockResolvedValue({ content: [{ id: 3, name: 'qtree-a' }], total: 1 });
  });

  it.each(resourceCases)('loads %s resources only for the current storage cluster', async (resourceType, api, row) => {
    const wrapper = shallowMount(ClusterResourceListTab, {
      props: { clusterId: 42, resourceType },
      global: { stubs: { DataTable } },
    });
    await flushPromises();

    expect(api.fetch).toHaveBeenCalledWith({ page: 1, size: 20, storage_cluster_id: 42 });
    expect(wrapper.findComponent(DataTable).props()).toMatchObject({
      data: [row],
      pagination: { page: 1, pageSize: 20, total: 1 },
    });
  });
});
