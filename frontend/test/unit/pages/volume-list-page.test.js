import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

const volumeApi = vi.hoisted(() => ({
  fetch: vi.fn(() => Promise.resolve({ content: [], total: 0 })),
}));

vi.mock('@/api/volume-api.js', () => ({ default: volumeApi }));
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

describe('VolumeListPage', () => {
  it('filters volumes by storage cluster and clears the filter on reset', async () => {
    const { default: VolumeListPage } = await import('@/pages/admin/volume/VolumeListPage.vue');
    const wrapper = shallowMount(VolumeListPage, {
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

    expect(volumeApi.fetch).toHaveBeenNthCalledWith(1, {
      page: 1,
      size: 20,
      storage_cluster_id: null,
    });

    const clusterSelect = wrapper.findComponent({ name: 'StorageClusterSelect' });
    expect(clusterSelect.props('clearable')).toBe(true);
    await clusterSelect.vm.$emit('update:modelValue', 12);
    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await flushPromises();

    expect(volumeApi.fetch).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      storage_cluster_id: 12,
    });

    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await flushPromises();

    expect(volumeApi.fetch).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      storage_cluster_id: null,
    });
  });
});
