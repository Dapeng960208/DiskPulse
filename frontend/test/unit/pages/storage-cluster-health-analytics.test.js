import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';
import StorageClusterDetailPage from '@/pages/admin/storage-cluster/StorageClusterDetailPage.vue';

const initialRange = ['2026-07-01 00:00:00', '2026-07-02 00:00:00'];
const storageClusterApi = vi.hoisted(() => ({
  fetchById: vi.fn(),
  fetchStorageRealTimeDataById: vi.fn(),
  fetchCapacityChange: vi.fn(),
  fetchErrorSeverity: vi.fn(),
  fetchTopLatency: vi.fn(),
  fetchRepeatedFaults: vi.fn(),
  fetchSystemEvents: vi.fn(),
  exportAnalytics: vi.fn(),
}));

vi.mock('@/api/storage-cluster-api', () => ({ default: storageClusterApi }));
const route = vi.hoisted(() => ({ name: 'StorageClusterDetail', params: { id: '42' } }));
vi.mock('vue-router', () => ({ useRoute: () => route }));
vi.mock('@/composables/common', () => ({ getDefaultTime: () => [...initialRange] }));

let mountedWrapper;

afterEach(() => {
  mountedWrapper?.unmount();
  mountedWrapper = null;
});

const passthrough = (name, tag = 'div') => defineComponent({
  name,
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    return () => h(tag, attrs, slots.default?.());
  },
});

const DatePicker = defineComponent({
  name: 'ElDatePicker',
  props: { modelValue: { type: Array, default: () => [] } },
  emits: ['update:modelValue'],
  setup() {
    return () => h('input', { 'data-testid': 'analytics-date-range' });
  },
});

const Tabs = defineComponent({
  name: 'ElTabs',
  props: { modelValue: { type: String, default: '' } },
  emits: ['update:modelValue'],
  setup(_, { slots }) {
    return () => h('div', { 'data-testid': 'analytics-tabs' }, slots.default?.());
  },
});

const TabPane = defineComponent({
  name: 'ElTabPane',
  props: { label: String, name: String },
  setup(props, { slots }) {
    return () => h('section', { 'data-tab': props.name }, [props.label, ...(slots.default?.() || [])]);
  },
});

const Dropdown = defineComponent({
  name: 'ElDropdown',
  emits: ['command'],
  setup(_, { slots }) {
    return () => h('div', { 'data-testid': 'analytics-export' }, [
      ...(slots.default?.() || []),
      ...(slots.dropdown?.() || []),
    ]);
  },
});

async function mountPage() {
  const wrapper = shallowMount(StorageClusterDetailPage, {
    attachTo: document.body,
    global: {
      stubs: {
        FilterForm: passthrough('FilterForm', 'form'),
        StorageClusterSelect: passthrough('StorageClusterSelect'),
        ElCard: passthrough('ElCard'),
        ElDescriptions: passthrough('ElDescriptions'),
        ElDescriptionsItem: passthrough('ElDescriptionsItem'),
        ElFormItem: passthrough('ElFormItem'),
        ElDatePicker: DatePicker,
        ElSelect: passthrough('ElSelect', 'select'),
        ElOption: passthrough('ElOption', 'option'),
        ElTabs: Tabs,
        ElTabPane: TabPane,
        ElDropdown: Dropdown,
        ElDropdownMenu: passthrough('ElDropdownMenu'),
        ElDropdownItem: passthrough('ElDropdownItem', 'button'),
        ElButton: passthrough('ElButton', 'button'),
        LineCharts: passthrough('LineCharts'),
        PieCharts: passthrough('PieCharts'),
        BarStackChart: passthrough('BarStackChart'),
        LoadingCharts: passthrough('LoadingCharts'),
        AnimatedTextChart: passthrough('AnimatedTextChart'),
      },
    },
  });
  await flushPromises();
  mountedWrapper = wrapper;
  return wrapper;
}

async function selectTab(wrapper, name) {
  await wrapper.findComponent({ name: 'ElTabs' }).vm.$emit('update:modelValue', name);
  await flushPromises();
}

describe('storage cluster health analytics page', () => {
  beforeEach(() => {
    route.name = 'StorageClusterDetail';
    route.params = { id: '42' };
    storageClusterApi.fetchById.mockResolvedValue({ id: 42, name: 'cluster-a', storage_type: 'netapp' });
    storageClusterApi.fetchStorageRealTimeDataById.mockResolvedValue({ data: [] });
    storageClusterApi.fetchCapacityChange.mockResolvedValue({ data: [] });
    storageClusterApi.fetchErrorSeverity.mockResolvedValue({ total: 0, counts: {} });
    storageClusterApi.fetchTopLatency.mockResolvedValue({ supported: true, data: [] });
    storageClusterApi.fetchRepeatedFaults.mockResolvedValue({ data: [] });
    storageClusterApi.fetchSystemEvents.mockResolvedValue({ data: [] });
    storageClusterApi.exportAnalytics.mockResolvedValue({
      data: new Blob(['report']),
      headers: { 'content-disposition': 'attachment; filename="storage-health.xlsx"' },
    });
  });

  it('shows three analytics tabs with one shared date range and loads capacity first', async () => {
    const wrapper = await mountPage();

    expect(wrapper.text()).toContain('容量趋势');
    expect(wrapper.text()).toContain('性能分析');
    expect(wrapper.text()).toContain('故障分析');
    expect(wrapper.findAllComponents({ name: 'ElDatePicker' })).toHaveLength(1);
    expect(storageClusterApi.fetchCapacityChange).toHaveBeenCalledWith(42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
    });
    expect(storageClusterApi.fetchTopLatency).not.toHaveBeenCalled();
    expect(storageClusterApi.fetchErrorSeverity).not.toHaveBeenCalled();
    expect(storageClusterApi.fetchRepeatedFaults).not.toHaveBeenCalled();
    expect(storageClusterApi.fetchSystemEvents).not.toHaveBeenCalled();
  });

  it('loads performance and fault data lazily and refreshes only the active tab for a new range', async () => {
    const wrapper = await mountPage();

    await selectTab(wrapper, 'performance');
    expect(storageClusterApi.fetchTopLatency).toHaveBeenCalledTimes(1);
    expect(storageClusterApi.fetchErrorSeverity).not.toHaveBeenCalled();

    const nextRange = ['2026-07-03 00:00:00', '2026-07-04 00:00:00'];
    await wrapper.findComponent({ name: 'ElDatePicker' }).vm.$emit('update:modelValue', nextRange);
    await flushPromises();
    expect(storageClusterApi.fetchTopLatency).toHaveBeenLastCalledWith(42, {
      start_time: nextRange[0],
      end_time: nextRange[1],
    });
    expect(storageClusterApi.fetchCapacityChange).toHaveBeenCalledTimes(1);

    await selectTab(wrapper, 'faults');
    expect(storageClusterApi.fetchErrorSeverity).toHaveBeenCalledTimes(1);
    expect(storageClusterApi.fetchRepeatedFaults).toHaveBeenCalledTimes(1);
    expect(storageClusterApi.fetchSystemEvents).toHaveBeenCalledTimes(1);

    await selectTab(wrapper, 'capacity');
    await selectTab(wrapper, 'faults');
    expect(storageClusterApi.fetchErrorSeverity).toHaveBeenCalledTimes(1);
    expect(storageClusterApi.fetchRepeatedFaults).toHaveBeenCalledTimes(1);
    expect(storageClusterApi.fetchSystemEvents).toHaveBeenCalledTimes(1);
  });

  it('shows vendor events as system events inside fault analysis', async () => {
    storageClusterApi.fetchSystemEvents.mockResolvedValue({
      data: [{
        source: 'netapp',
        severity: 'error',
        event_code: 'sec.authsys.lookup.failed',
        object_id: 'SVM_nas',
        description: 'Unable to retrieve credentials',
        occurred_at: '2026-07-14 18:54:00',
      }],
    });
    const wrapper = await mountPage();

    await selectTab(wrapper, 'faults');

    expect(wrapper.text()).toContain('系统事件');
    expect(wrapper.text()).toContain('Unable to retrieve credentials');
    expect(wrapper.text()).not.toContain('扩容');
  });

  it('shows unsupported performance and empty fault states', async () => {
    storageClusterApi.fetchTopLatency.mockResolvedValue({ supported: false, data: [] });
    const wrapper = await mountPage();

    await selectTab(wrapper, 'performance');
    expect(wrapper.text()).toContain('不支持性能分析');

    await selectTab(wrapper, 'faults');
    expect(wrapper.text()).toContain('暂无故障');
  });

  it('exports the current section or the complete report and downloads the returned blob', async () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    const wrapper = await mountPage();
    const dropdown = wrapper.findComponent({ name: 'ElDropdown' });

    await dropdown.vm.$emit('command', 'current:csv');
    await flushPromises();
    expect(storageClusterApi.exportAnalytics).toHaveBeenNthCalledWith(1, 42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
      section: 'capacity',
      format: 'csv',
    });
    expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(clickSpy).toHaveBeenCalledTimes(1);

    await selectTab(wrapper, 'performance');
    await dropdown.vm.$emit('command', 'current:pdf');
    await flushPromises();
    expect(storageClusterApi.exportAnalytics).toHaveBeenNthCalledWith(2, 42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
      section: 'latency',
      format: 'pdf',
    });

    await selectTab(wrapper, 'faults');
    await dropdown.vm.$emit('command', 'severity:csv');
    await flushPromises();
    expect(storageClusterApi.exportAnalytics).toHaveBeenNthCalledWith(3, 42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
      section: 'severity',
      format: 'csv',
    });

    await dropdown.vm.$emit('command', 'all:excel');
    await flushPromises();
    expect(storageClusterApi.exportAnalytics).toHaveBeenNthCalledWith(4, 42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
      section: 'all',
      format: 'excel',
    });
    expect(clickSpy).toHaveBeenCalledTimes(4);
    clickSpy.mockRestore();
  });

  it('offers cluster selection from the standalone storage health entry', async () => {
    route.name = 'StorageHealth';
    route.params = {};
    const wrapper = await mountPage();
    const selector = wrapper.findComponent({ name: 'StorageClusterSelect' });

    expect(selector.exists()).toBe(true);
    expect(storageClusterApi.fetchCapacityChange).not.toHaveBeenCalled();

    await selector.vm.$emit('update:modelValue', 7);
    await flushPromises();

    expect(storageClusterApi.fetchById).toHaveBeenCalledWith(7);
    expect(storageClusterApi.fetchCapacityChange).toHaveBeenCalledWith(7, {
      start_time: initialRange[0],
      end_time: initialRange[1],
    });
  });
});
