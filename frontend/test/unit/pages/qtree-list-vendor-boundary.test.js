import { defineComponent, h, ref } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';
import { ElMessage } from 'element-plus';

const { qtreeApi, storageClusterApi } = vi.hoisted(() => ({
  qtreeApi: { fetch: vi.fn(() => Promise.resolve({ content: [], total: 0 })) },
  storageClusterApi: {
    fetchById: vi.fn((id) => Promise.resolve({ id, storage_type: 'isilon' })),
  },
}));
const warning = vi.spyOn(ElMessage, 'warning').mockImplementation(() => undefined);

vi.mock('@/api/qtree-api.js', () => ({ default: qtreeApi }));
vi.mock('@/api/storage-cluster-api', () => ({ default: storageClusterApi }));
vi.mock('@/utils/authorization', () => ({ hasRole: () => false }));
vi.mock('vue-router', async () => ({
  ...(await vi.importActual('vue-router')),
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock('@/components/form/QueryForm.vue', () => ({ default: { name: 'FilterForm', template: '<form />' } }));
vi.mock('@/components/data/DataTable.vue', () => ({ default: { name: 'DataTable', template: '<div />' } }));
vi.mock('@/components/form/Progress.vue', () => ({ default: { name: 'Progress', template: '<div />' } }));
vi.mock('@/components/form/StorageClusterSelect.vue', () => ({
  default: { name: 'StorageClusterSelect', props: ['modelValue'], template: '<select />' },
}));
vi.mock('@/components/form/VolumeSelect.vue', () => ({
  default: {
    name: 'VolumeSelect',
    props: ['modelValue', 'storageClusterId'],
    template: '<select />',
  },
}));
vi.mock('@/composables/query', () => ({
  useQuery: (request, initialValue) => {
    const result = ref(initialValue);
    return {
      result,
      querying: ref(false),
      query: vi.fn(async () => {
        result.value = await request();
        return result.value;
      }),
    };
  },
  useQueryParams: (provider) => {
    const queryParams = ref(provider());
    return {
      queryParams,
      reset: vi.fn(() => { queryParams.value = provider(); }),
    };
  },
}));

const passthrough = (name, tag = 'div') => defineComponent({
  name,
  setup(_, { slots }) {
    return () => h(tag, slots.default?.());
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
  props: { modelValue: { type: Number, default: null } },
  emits: ['update:modelValue'],
  template: '<select />',
});

const VolumeSelect = defineComponent({
  name: 'VolumeSelect',
  props: {
    modelValue: { type: Number, default: null },
    storageClusterId: { type: Number, default: null },
  },
  emits: ['update:modelValue'],
  template: '<select />',
});

async function mountPage() {
  const { default: QtreeListPage } = await import('@/pages/admin/qtree/QtreeListPage.vue');
  const wrapper = shallowMount(QtreeListPage, {
    global: {
      stubs: {
        FilterForm,
        StorageClusterSelect,
        VolumeSelect,
        DataTable: passthrough('DataTable'),
        ElFormItem: passthrough('ElFormItem'),
        ElInput: passthrough('ElInput', 'input'),
        ElTableColumn: defineComponent({ name: 'ElTableColumn', template: '<div />' }),
        ElTag: passthrough('ElTag'),
        ElButton: passthrough('ElButton', 'button'),
        Progress: passthrough('Progress'),
      },
    },
  });
  await flushPromises();
  return wrapper;
}

describe('Qtree vendor boundary', () => {
  beforeEach(() => vi.clearAllMocks());

  it('warns and does not query Qtrees for an Isilon cluster', async () => {
    const wrapper = await mountPage();
    expect(qtreeApi.fetch).toHaveBeenCalledTimes(1);

    wrapper.findComponent({ name: 'StorageClusterSelect' }).vm.$emit('update:modelValue', 7);
    await flushPromises();
    wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await flushPromises();

    expect(qtreeApi.fetch).toHaveBeenCalledTimes(1);
    expect(warning).toHaveBeenCalledWith('Isilon 不支持 Qtree');
  });

  it('scopes the storage-space selector to the selected cluster', async () => {
    const wrapper = await mountPage();
    wrapper.findComponent({ name: 'StorageClusterSelect' }).vm.$emit('update:modelValue', 7);
    await flushPromises();

    expect(wrapper.findComponent({ name: 'VolumeSelect' }).props('storageClusterId')).toBe(7);
  });
});
