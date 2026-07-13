import { defineComponent, h, reactive } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { vi } from 'vitest';

const route = reactive({ params: { id: '7' } });
const fixedRange = ['2026-07-01 00:00:00', '2026-07-01 08:00:00'];

const storageClusterApi = {
  fetchById: vi.fn(() => Promise.resolve({ id: 7, name: 'cluster-a' })),
  fetchStorageRealTimeDataById: vi.fn(() => Promise.resolve({
    data: [{ time: '2026-07-01 08:00:00', value: 1 }],
  })),
};

const realtimeApi = {
  fetchStorageRealTimeDataById: vi.fn((id) => Promise.resolve({
    info: {
      id,
      linux_path: `/group/user-${id}`,
      name: `usage-${id}`,
      limit: 100,
      used: 20,
      use_ratio: 20,
    },
    data: [{ time: '2026-07-01 08:00:00', value: id }],
  })),
};

const alertApi = {
  fetch: vi.fn(({ related_id: id }) => Promise.resolve({
    content: [{
      id,
      description: `alert-${id}`,
      updated_at: `2026-07-0${id} 08:00:00`,
    }],
  })),
};

vi.mock('vue-router', () => ({ useRoute: () => route }));
vi.mock('@/composables/common', () => ({
  getDefaultTime: vi.fn(() => [...fixedRange]),
}));
vi.mock('@/api/storage-cluster-api', () => ({ default: storageClusterApi }));
vi.mock('@/api/storage-usage-api.js', () => ({ default: realtimeApi }));
vi.mock('@/api/alert-api.js', () => ({ default: alertApi }));
vi.mock('@/api/group-api.js', () => ({ default: realtimeApi }));
vi.mock('@/api/qtree-api.js', () => ({ default: realtimeApi }));
vi.mock('@/api/volume-api.js', () => ({ default: realtimeApi }));
vi.mock('@/api/aggregate-api.js', () => ({ default: realtimeApi }));
vi.mock('@/api/project-api.js', () => ({ default: realtimeApi }));
vi.mock('@/api/project-storage-environment-api', () => ({ default: realtimeApi }));

const FilterFormStub = defineComponent({
  name: 'FilterForm',
  emits: ['query', 'reset'],
  setup(_, { slots }) {
    return () => h('form', slots.default?.());
  },
});

function emptyStub(name) {
  return defineComponent({
    name,
    props: {
      data: { type: [Array, Object], default: null },
      yAxisUnit: { type: String, default: '' },
    },
    setup(_, { slots }) {
      return () => h('div', slots.default?.());
    },
  });
}

function selectStub(name) {
  return defineComponent({
    name,
    props: {
      modelValue: { type: [Number, String, Array], default: null },
    },
    emits: ['update:modelValue'],
    setup(_, { slots }) {
      return () => h('div', slots.default?.());
    },
  });
}

vi.mock('@/components/form/QueryForm.vue', () => ({ default: FilterFormStub }));
vi.mock('@/common/charts/LineCharts.vue', () => ({ default: emptyStub('LineCharts') }));
vi.mock('@/common/charts/MultipleLineCharts.vue', () => ({ default: emptyStub('MultipleLineCharts') }));
vi.mock('@/common/charts/LoadingCharts.vue', () => ({ default: emptyStub('LoadingCharts') }));
vi.mock('@/common/charts/AnimatedTextChart.vue', () => ({ default: emptyStub('AnimatedTextChart') }));
vi.mock('@/components/form/QtreeSelect.vue', () => ({ default: selectStub('QtreeSelect') }));
vi.mock('@/components/form/VolumeSelect.vue', () => ({ default: selectStub('VolumeSelect') }));
vi.mock('@/components/form/AggregateSelect.vue', () => ({ default: selectStub('AggregateSelect') }));
vi.mock('@/components/form/ProjectSelect.vue', () => ({ default: selectStub('ProjectSelect') }));
vi.mock('@/components/form/StorageUsageSelect.vue', () => ({ default: selectStub('StorageUsageSelect') }));
vi.mock('@/components/form/GroupSelect.vue', () => ({ default: selectStub('GroupSelect') }));
vi.mock('@/components/form/RdUserSelect.vue', () => ({ default: selectStub('RdUserSelect') }));

const ElDatePickerStub = defineComponent({
  name: 'ElDatePicker',
  props: {
    modelValue: { type: Array, default: () => [] },
    shortcuts: { type: Array, default: () => [] },
  },
  emits: ['update:modelValue'],
  setup() {
    return () => h('div');
  },
});

const ElSelectStub = defineComponent({
  name: 'ElSelect',
  props: {
    modelValue: { type: [Number, String, Array], default: null },
  },
  emits: ['update:modelValue'],
  setup(_, { slots }) {
    return () => h('div', slots.default?.());
  },
});

const slotStub = (name) => defineComponent({
  name,
  setup(_, { slots }) {
    return () => h('div', slots.default?.());
  },
});

const noSlotStub = (name) => defineComponent({
  name,
  setup() {
    return () => h('div');
  },
});

const pageStubs = {
  ElCard: slotStub('ElCard'),
  ElCol: slotStub('ElCol'),
  ElDatePicker: ElDatePickerStub,
  ElDescriptions: slotStub('ElDescriptions'),
  ElDescriptionsItem: slotStub('ElDescriptionsItem'),
  ElFormItem: slotStub('ElFormItem'),
  ElOption: slotStub('ElOption'),
  ElRow: slotStub('ElRow'),
  ElSelect: ElSelectStub,
  ElTable: slotStub('ElTable'),
  ElTableColumn: noSlotStub('ElTableColumn'),
  ElTag: slotStub('ElTag'),
};

describe('project environment page function coverage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('executes storage cluster detail shortcuts, watchers, query, and reset', async () => {
    const { default: StorageClusterDetailPage } = await import(
      '@/pages/admin/storage-cluster/StorageClusterDetailPage.vue'
    );
    const wrapper = mount(StorageClusterDetailPage, {
      global: { stubs: pageStubs },
    });
    await flushPromises();

    expect(storageClusterApi.fetchById).toHaveBeenCalledWith(7);
    expect(storageClusterApi.fetchStorageRealTimeDataById).toHaveBeenCalledWith(
      7,
      expect.objectContaining({ indicator: 'used' }),
    );

    const datePicker = wrapper.findComponent({ name: 'ElDatePicker' });
    datePicker.props('shortcuts').forEach((shortcut) => shortcut.value());
    datePicker.vm.$emit('update:modelValue', [
      '2026-07-02 00:00:00',
      '2026-07-02 08:00:00',
    ]);
    wrapper.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'use_ratio');
    wrapper.findComponent(FilterFormStub).vm.$emit('query');
    wrapper.findComponent(FilterFormStub).vm.$emit('reset');
    await flushPromises();

    expect(storageClusterApi.fetchStorageRealTimeDataById).toHaveBeenLastCalledWith(
      7,
      expect.objectContaining({ indicator: 'used' }),
    );
  });

  it('executes realtime shortcuts, filter handlers, and attribute watchers', async () => {
    const { default: RealTimePage } = await import('@/pages/common/RealTimePage.vue');
    const wrapper = mount(RealTimePage, {
      props: {
        apiType: 'storage-usage',
        label: '用户目录',
        attributeId: [1, 2],
      },
      global: { stubs: pageStubs },
    });
    await flushPromises();

    const datePicker = wrapper.findComponent({ name: 'ElDatePicker' });
    datePicker.props('shortcuts').forEach((shortcut) => shortcut.value());
    datePicker.vm.$emit('update:modelValue', [
      '2026-07-03 00:00:00',
      '2026-07-03 08:00:00',
    ]);
    wrapper.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'file_used');
    wrapper.findComponent(FilterFormStub).vm.$emit('query');
    wrapper.findComponent(FilterFormStub).vm.$emit('reset');
    await wrapper.setProps({ attributeId: 3 });
    await flushPromises();

    expect(realtimeApi.fetchStorageRealTimeDataById).toHaveBeenCalledWith(
      3,
      expect.objectContaining({ indicator: 'used' }),
    );
    expect(alertApi.fetch).toHaveBeenCalledWith({
      related_type: 'StorageUsage',
      related_id: 3,
    });
  });
});
