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
vi.mock('@/components/basic/AccessibleResourceLink.vue', () => ({
  default: { name: 'AccessibleResourceLink', render: () => null },
}));
vi.mock('@/components/form/Progress.vue', () => ({
  default: { name: 'Progress', render: () => null },
}));

const DataTable = defineComponent({
  name: 'DataTable',
  props: {
    data: { type: Array, default: () => [] },
    loading: Boolean,
    pagination: { type: Object, default: () => ({}) },
    error: { type: String, default: '' },
  },
  emits: ['update:pagination'],
  setup(props, { slots }) {
    return () => h('section', { 'data-testid': 'cluster-resource-table' }, [
      JSON.stringify(props.data),
      ...(slots.default?.() || []),
    ]);
  },
});

const QueryForm = defineComponent({
  name: 'QueryForm',
  emits: ['query', 'reset'],
  setup(_, { slots }) {
    return () => h('form', slots.default?.());
  },
});

const Input = defineComponent({
  name: 'ElInput',
  props: { modelValue: { type: String, default: '' } },
  emits: ['update:modelValue'],
  setup() {
    return () => h('input');
  },
});

const FormItem = defineComponent({
  name: 'ElFormItem',
  setup(_, { slots }) {
    return () => h('div', slots.default?.());
  },
});

const VolumeSelect = defineComponent({
  name: 'VolumeSelect',
  props: { modelValue: { type: [Number, null], default: null } },
  emits: ['update:modelValue'],
  setup() {
    return () => h('select');
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

  it('updates the server-side page while preserving the current cluster boundary', async () => {
    const wrapper = shallowMount(ClusterResourceListTab, {
      props: { clusterId: 42, resourceType: 'aggregate' },
      global: { stubs: { DataTable } },
    });
    await flushPromises();

    await wrapper.findComponent(DataTable).vm.$emit('update:pagination', {
      page: 2,
      pageSize: 50,
      prop: 'name',
      order: 'ascending',
    });
    await flushPromises();

    expect(aggregateApi.fetch).toHaveBeenLastCalledWith({
      page: 2,
      size: 50,
      prop: 'name',
      order: 'ascending',
      storage_cluster_id: 42,
    });
  });

  it('uses the standard filter form without allowing the cluster boundary to be cleared', async () => {
    const wrapper = shallowMount(ClusterResourceListTab, {
      props: { clusterId: 42, resourceType: 'aggregate' },
      global: { stubs: { DataTable, QueryForm, ElFormItem: FormItem, ElInput: Input, 'el-input': Input } },
    });
    await flushPromises();

    await wrapper.findComponent({ name: 'ElInput' }).vm.$emit('update:modelValue', 'pool-a');
    await wrapper.findComponent(QueryForm).vm.$emit('query');
    await flushPromises();
    expect(aggregateApi.fetch).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      nameLike: 'pool-a',
      storage_cluster_id: 42,
    });

    await wrapper.findComponent(QueryForm).vm.$emit('reset');
    await flushPromises();
    expect(aggregateApi.fetch).toHaveBeenLastCalledWith({ page: 1, size: 20, storage_cluster_id: 42 });
  });

  it('scopes the Qtree storage-space filter to the current cluster', async () => {
    const wrapper = shallowMount(ClusterResourceListTab, {
      props: { clusterId: 42, resourceType: 'qtree' },
      global: {
        stubs: {
          DataTable,
          QueryForm,
          ElFormItem: FormItem,
          ElInput: Input,
          'el-input': Input,
          VolumeSelect,
        },
      },
    });
    await flushPromises();

    await wrapper.findComponent(VolumeSelect).vm.$emit('update:modelValue', 6);
    await wrapper.findComponent(QueryForm).vm.$emit('query');
    await flushPromises();

    expect(qtreeApi.fetch).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      volume_id: 6,
      storage_cluster_id: 42,
    });
  });

  it('keeps a failed resource query actionable inside the current detail tab', async () => {
    volumeApi.fetch.mockRejectedValueOnce(new Error('network'));
    const wrapper = shallowMount(ClusterResourceListTab, {
      props: { clusterId: 42, resourceType: 'volume' },
      global: { stubs: { DataTable } },
    });
    await flushPromises();

    expect(wrapper.findComponent(DataTable).props('error')).toBe('加载存储空间失败，请稍后重试');
  });
});
