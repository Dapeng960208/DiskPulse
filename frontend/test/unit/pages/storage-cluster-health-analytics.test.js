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
const aggregateApi = vi.hoisted(() => ({
  fetchAggregateTrees: vi.fn(),
}));

vi.mock('@/api/storage-cluster-api', () => ({ default: storageClusterApi }));
vi.mock('@/api/aggregate-api.js', () => ({ default: aggregateApi }));
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

const Input = defineComponent({
  name: 'ElInput',
  props: { modelValue: { type: String, default: '' }, placeholder: String },
  emits: ['update:modelValue'],
  setup(props) {
    return () => h('input', { value: props.modelValue, placeholder: props.placeholder });
  },
});

const Select = defineComponent({
  name: 'ElSelect',
  props: { modelValue: { type: String, default: '' }, placeholder: String },
  emits: ['update:modelValue'],
  setup(props, { slots }) {
    return () => h('select', { value: props.modelValue }, slots.default?.());
  },
});

const Pagination = defineComponent({
  name: 'ElPagination',
  props: {
    currentPage: { type: Number, default: 1 },
    pageSize: { type: Number, default: 20 },
    total: { type: Number, default: 0 },
  },
  emits: ['current-change', 'size-change'],
  setup(props) {
    return () => h('nav', { 'data-testid': 'system-event-pagination' }, `${props.total}`);
  },
});

const Table = defineComponent({
  name: 'ElTable',
  props: { data: { type: Array, default: () => [] } },
  setup(props, { slots }) {
    return () => h('div', [JSON.stringify(props.data), ...(slots.default?.() || [])]);
  },
});

const DiskUsage = defineComponent({
  name: 'DiskUsage',
  props: { data: { type: Array, default: () => [] } },
  setup() {
    return () => h('div');
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

const FilterForm = defineComponent({
  name: 'FilterForm',
  emits: ['query', 'reset'],
  setup(_, { slots }) {
    return () => h('form', [
      ...(slots.default?.() || []),
      h('div', { 'data-testid': 'filter-actions' }, slots.actions?.()),
    ]);
  },
});

async function mountPage() {
  const wrapper = shallowMount(StorageClusterDetailPage, {
    attachTo: document.body,
    global: {
      directives: {
        loading: () => {},
      },
      stubs: {
        FilterForm,
        StorageClusterSelect: passthrough('StorageClusterSelect'),
        ElCard: passthrough('ElCard'),
        ElDescriptions: passthrough('ElDescriptions'),
        ElDescriptionsItem: passthrough('ElDescriptionsItem'),
        ElFormItem: passthrough('ElFormItem'),
        ElDatePicker: DatePicker,
        ElInput: Input,
        ElSelect: Select,
        ElOption: passthrough('ElOption', 'option'),
        ElPagination: Pagination,
        ElTable: Table,
        ElTabs: Tabs,
        ElTabPane: TabPane,
        ElDropdown: Dropdown,
        ElDropdownMenu: passthrough('ElDropdownMenu'),
        ElDropdownItem: passthrough('ElDropdownItem', 'button'),
        ElButton: passthrough('ElButton', 'button'),
        LineCharts: passthrough('LineCharts'),
        PieCharts: passthrough('PieCharts'),
        BarStackChart: passthrough('BarStackChart'),
        DiskUsage,
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
    storageClusterApi.fetchSystemEvents.mockResolvedValue({
      data: [], total: 0, page: 1, page_size: 20,
    });
    aggregateApi.fetchAggregateTrees.mockResolvedValue({ data: [{ name: 'volume-a' }] });
    storageClusterApi.exportAnalytics.mockResolvedValue({
      data: new Blob(['report']),
      headers: { 'content-disposition': 'attachment; filename="storage-health.xlsx"' },
    });
  });

  it('shows storage distribution beside capacity and loads capacity first', async () => {
    const wrapper = await mountPage();

    expect(wrapper.text()).toContain('容量趋势');
    expect(wrapper.text()).toContain('存储分布');
    expect(wrapper.text()).toContain('性能分析');
    expect(wrapper.text()).toContain('故障分析');
    expect(wrapper.findAllComponents({ name: 'ElDatePicker' })).toHaveLength(1);
    expect(wrapper.get('[data-testid="filter-actions"] [data-testid="analytics-export"]').exists()).toBe(true);
    expect(storageClusterApi.fetchCapacityChange).toHaveBeenCalledWith(42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
    });
    expect(storageClusterApi.fetchTopLatency).not.toHaveBeenCalled();
    expect(storageClusterApi.fetchErrorSeverity).not.toHaveBeenCalled();
    expect(storageClusterApi.fetchRepeatedFaults).not.toHaveBeenCalled();
    expect(storageClusterApi.fetchSystemEvents).not.toHaveBeenCalled();
    expect(aggregateApi.fetchAggregateTrees).not.toHaveBeenCalled();
  });

  it('loads the current cluster storage distribution once when its tab opens', async () => {
    const wrapper = await mountPage();

    await selectTab(wrapper, 'distribution');

    expect(aggregateApi.fetchAggregateTrees).toHaveBeenCalledWith({
      storage_cluster_id: 42,
    });
    expect(wrapper.findComponent({ name: 'DiskUsage' }).props('data')).toEqual([
      { name: 'volume-a' },
    ]);

    await selectTab(wrapper, 'capacity');
    await selectTab(wrapper, 'distribution');
    expect(aggregateApi.fetchAggregateTrees).toHaveBeenCalledTimes(1);
  });

  it('keeps the time filter inside supported tabs and gives the primary charts enough room', async () => {
    storageClusterApi.fetchCapacityChange.mockResolvedValue({
      data: [{ updated_at: initialRange[0], used: 100 }],
    });
    const wrapper = await mountPage();
    const tabs = wrapper.get('[data-testid="analytics-tabs"]');
    const datePicker = tabs.findComponent({ name: 'ElDatePicker' });

    expect(tabs.find('.storage-health-filter').exists()).toBe(true);
    expect(datePicker.attributes('format')).toBe('YYYY-MM-DD HH:mm:ss');
    expect(datePicker.attributes('start-placeholder')).toBe('开始日期时间');
    expect(datePicker.attributes('end-placeholder')).toBe('结束日期时间');
    expect(wrapper.findComponent({ name: 'LineCharts' }).attributes('height')).toBe('520px');

    await selectTab(wrapper, 'distribution');

    expect(tabs.find('.storage-health-filter').exists()).toBe(false);
    expect(wrapper.findComponent({ name: 'DiskUsage' }).attributes('height')).toBe('520px');
  });

  it('uses the standard centered loading state for storage distribution', async () => {
    let resolveDistribution;
    aggregateApi.fetchAggregateTrees.mockReturnValue(new Promise((resolve) => {
      resolveDistribution = resolve;
    }));
    const wrapper = await mountPage();

    await selectTab(wrapper, 'distribution');

    expect(wrapper.get('.analytics-chart-stage').attributes('aria-busy')).toBe('true');
    expect(wrapper.findComponent({ name: 'LoadingCharts' }).exists()).toBe(false);

    resolveDistribution({ data: [{ name: 'volume-a' }] });
    await flushPromises();
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
      object_type: 'volume',
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
      total: 1,
      page: 1,
      page_size: 20,
      data: [{
        source: 'netapp',
        severity: 'error',
        event_code: 'sec.authsys.lookup.failed',
        object_id: 'SVM_nas',
        object_name: 'node-a',
        description: 'Unable to retrieve credentials',
        occurred_at: '2026-07-14 18:54:00',
      }],
    });
    const wrapper = await mountPage();

    await selectTab(wrapper, 'faults');

    expect(wrapper.text()).toContain('系统事件');
    expect(wrapper.text()).toContain('Unable to retrieve credentials');
    expect(wrapper.html()).toContain('label="事件对象"');
    expect(wrapper.html()).toContain('prop="object_name"');
    expect(wrapper.text()).not.toContain('扩容');
  });

  it('searches and paginates system events with 20 rows by default', async () => {
    storageClusterApi.fetchSystemEvents.mockResolvedValue({
      data: [], total: 45, page: 1, page_size: 20,
    });
    const wrapper = await mountPage();

    await selectTab(wrapper, 'faults');

    expect(storageClusterApi.fetchSystemEvents).toHaveBeenLastCalledWith(42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
      page: 1,
      page_size: 20,
    });
    const eventSection = wrapper.get('.system-events');
    const eventFilter = eventSection.findComponent({ name: 'FilterForm' });
    expect(eventFilter.exists()).toBe(true);
    expect(eventSection.findComponent({ name: 'ElInput' }).props('placeholder')).toBe('事件代码、对象或内容');
    expect(eventSection.findComponent({ name: 'ElSelect' }).props('placeholder')).toBe('全部等级');

    await eventSection.findComponent({ name: 'ElInput' }).vm.$emit('update:modelValue', 'quota');
    await eventSection.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'warning');
    await eventFilter.vm.$emit('query');
    await flushPromises();

    expect(storageClusterApi.fetchSystemEvents).toHaveBeenLastCalledWith(42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
      keyword: 'quota',
      severity: 'warning',
      page: 1,
      page_size: 20,
    });

    const pagination = eventSection.findComponent({ name: 'ElPagination' });
    expect(pagination.props()).toMatchObject({ currentPage: 1, pageSize: 20, total: 45 });
    await pagination.vm.$emit('current-change', 2);
    await flushPromises();

    expect(storageClusterApi.fetchSystemEvents).toHaveBeenLastCalledWith(42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
      keyword: 'quota',
      severity: 'warning',
      page: 2,
      page_size: 20,
    });
  });

  it('explains never-collected performance and empty fault states', async () => {
    storageClusterApi.fetchTopLatency.mockResolvedValue({ supported: false, data: [] });
    const wrapper = await mountPage();

    await selectTab(wrapper, 'performance');
    expect(wrapper.text()).toContain('尚未采集到性能数据');
    expect(wrapper.text()).toContain('设备 API 权限');

    await selectTab(wrapper, 'faults');
    expect(wrapper.text()).toContain('当前时间范围内暂无故障数据');
    expect(wrapper.text()).toContain('厂商事件采集权限');
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

  it('keeps analytics inside the storage cluster detail without a selector or config summary', async () => {
    const wrapper = await mountPage();

    expect(wrapper.findComponent({ name: 'StorageClusterSelect' }).exists()).toBe(false);
    expect(wrapper.findComponent({ name: 'ElDescriptions' }).exists()).toBe(false);
    expect(storageClusterApi.fetchById).toHaveBeenCalledWith(42);
  });
});
