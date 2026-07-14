import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

const resourceApis = vi.hoisted(() => Object.fromEntries(
  ['volume', 'aggregate', 'qtree'].map((resource) => [resource, {
    fetch: vi.fn(() => Promise.resolve({ content: [], total: 0 })),
  }]),
));
const storageClusterApi = vi.hoisted(() => ({
  fetchById: vi.fn((id) => Promise.resolve({ id, storage_type: 'netapp' })),
}));

vi.mock('@/api/volume-api.js', () => ({ default: resourceApis.volume }));
vi.mock('@/api/aggregate-api.js', () => ({ default: resourceApis.aggregate }));
vi.mock('@/api/qtree-api.js', () => ({ default: resourceApis.qtree }));
vi.mock('@/api/storage-cluster-api', () => ({ default: storageClusterApi }));
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
vi.mock('@/components/form/VolumeSelect.vue', () => ({
  default: { name: 'VolumeSelect', template: '<select />' },
}));
vi.mock('@/utils/authorization', () => ({ hasRole: () => false }));
vi.mock('vue-router', async () => ({
  ...(await vi.importActual('vue-router')),
  useRouter: () => ({ push: vi.fn() }),
}));

const passthrough = (name) => defineComponent({
  name,
  setup(_, { slots }) {
    return () => h('div', slots.default?.());
  },
});

const FilterForm = defineComponent({
  name: 'FilterForm',
  emits: ['query', 'reset'],
  setup(_, { slots }) {
    return () => h('form', slots.default?.());
  },
});

const StorageClusterSelect = defineComponent({
  name: 'StorageClusterSelect',
  props: {
    modelValue: { type: Number, default: null },
    clearable: Boolean,
  },
  emits: ['update:modelValue'],
  setup() {
    return () => h('select');
  },
});

async function mountPage(loadPage) {
  const Page = await loadPage();
  const wrapper = shallowMount(Page, {
      global: {
        stubs: {
          FilterForm,
          StorageClusterSelect,
          DataTable: passthrough('DataTable'),
          ElFormItem: passthrough('ElFormItem'),
          ElInput: passthrough('ElInput'),
          ElTableColumn: defineComponent({ name: 'ElTableColumn', template: '<div />' }),
          ElTag: passthrough('ElTag'),
          ElButton: passthrough('ElButton'),
          Progress: passthrough('Progress'),
          RouterLink: passthrough('RouterLink'),
        },
      },
    });
  await flushPromises();
  return wrapper;
}

describe('storage resource list cluster filters', () => {
  it.each([
    ['volumes', () => import('@/pages/admin/volume/VolumeListPage.vue').then(({ default: page }) => page), resourceApis.volume],
    ['aggregates', () => import('@/pages/admin/aggregate/AggregateListPage.vue').then(({ default: page }) => page), resourceApis.aggregate],
    ['qtrees', () => import('@/pages/admin/qtree/QtreeListPage.vue').then(({ default: page }) => page), resourceApis.qtree],
  ])('filters %s by storage cluster and clears the filter on reset', async (_, loadPage, api) => {
    const wrapper = await mountPage(loadPage);

    expect(api.fetch).toHaveBeenNthCalledWith(1, {
      page: 1,
      size: 20,
      storage_cluster_id: null,
    });

    const clusterSelect = wrapper.findComponent({ name: 'StorageClusterSelect' });
    expect(clusterSelect.props('clearable')).toBe(true);
    await clusterSelect.vm.$emit('update:modelValue', 12);
    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await flushPromises();

    expect(api.fetch).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      storage_cluster_id: 12,
    });

    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await flushPromises();

    expect(api.fetch).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      storage_cluster_id: null,
    });
  });
});
