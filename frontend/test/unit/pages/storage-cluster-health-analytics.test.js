import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { vi } from 'vitest';
import StorageClusterDetailPage from '@/pages/admin/storage-cluster/StorageClusterDetailPage.vue';
import storageClusterDetailSource from '@/pages/admin/storage-cluster/StorageClusterDetailPage.vue?raw';

const initialRange = ['2026-07-01 00:00:00', '2026-07-02 00:00:00'];
const storageClusterApi = vi.hoisted(() => ({
  fetchById: vi.fn(),
  fetchStorageRealTimeDataById: vi.fn(),
  fetchCapacityChange: vi.fn(),
  fetchErrorSeverity: vi.fn(),
  fetchTopLatency: vi.fn(),
  fetchRepeatedFaults: vi.fn(),
  fetchSystemEvents: vi.fn(),
  fetchSystemEventDetail: vi.fn(),
  exportAnalytics: vi.fn(),
}));
const aggregateApi = vi.hoisted(() => ({
  fetchAggregateTrees: vi.fn(),
}));
const incidentApi = vi.hoisted(() => ({
  fetchIncidents: vi.fn(),
}));

vi.mock('@/api/storage-cluster-api', () => ({ default: storageClusterApi }));
vi.mock('@/api/aggregate-api.js', () => ({ default: aggregateApi }));
vi.mock('@/api/incident-api.js', () => ({ default: incidentApi }));
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
  props: { modelValue: { type: [String, Number, Array], default: '' }, placeholder: String },
  emits: ['update:modelValue'],
  setup(props, { slots }) {
    return () => h('select', { value: props.modelValue }, slots.default?.());
  },
});

const Tooltip = defineComponent({
  name: 'ElTooltip',
  setup(_, { slots }) {
    return () => h('div', { 'data-testid': 'association-tooltip' }, [
      ...(slots.default?.() || []),
      h('div', { class: 'association-tooltip__content' }, slots.content?.()),
    ]);
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

let tableRow;

const TableColumn = defineComponent({
  name: 'ElTableColumn',
  setup(_, { slots }) {
    return () => h('div', [slots.header?.(), slots.default?.({ row: tableRow })]);
  },
});

const DiskUsage = defineComponent({
  name: 'DiskUsage',
  props: { data: { type: Array, default: () => [] } },
  setup() {
    return () => h('div');
  },
});

const BarStackChart = defineComponent({
  name: 'BarStackChart',
  props: {
    data: { type: Array, default: () => [] },
    categories: { type: Array, default: () => [] },
    seriesNames: { type: Array, default: () => [] },
    seriesMap: { type: Object, default: () => ({}) },
    title: String,
    unit: String,
  },
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
      plugins: [createPinia()],
      directives: {
        loading: () => {},
      },
      stubs: {
        FilterForm,
        StorageClusterSelect: passthrough('StorageClusterSelect'),
        ElCard: passthrough('ElCard'),
        ElDescriptions: passthrough('ElDescriptions'),
        ElDescriptionsItem: passthrough('ElDescriptionsItem'),
        ElDialog: passthrough('ElDialog'),
        ElFormItem: passthrough('ElFormItem'),
        ElDatePicker: DatePicker,
        ElInput: Input,
        ElSelect: Select,
        ElOption: passthrough('ElOption', 'option'),
        ElTooltip: Tooltip,
        ElPagination: Pagination,
        ElTable: Table,
        ElTableColumn: TableColumn,
        ElTag: passthrough('ElTag'),
        TableActionButton: passthrough('TableActionButton', 'button'),
        ElTabs: Tabs,
        ElTabPane: TabPane,
        ElDropdown: Dropdown,
        ElDropdownMenu: passthrough('ElDropdownMenu'),
        ElDropdownItem: passthrough('ElDropdownItem', 'button'),
        ElButton: passthrough('ElButton', 'button'),
        StorageTrendChart: defineComponent({
          name: 'StorageTrendChart',
          props: { series: Array, indicator: String, trendMeta: Object, unit: String, ariaLabel: String, height: String },
          template: '<div class="storage-trend-chart-stub" />',
        }),
        PieCharts: passthrough('PieCharts'),
        BarStackChart,
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
    tableRow = {
      id: 91,
      sample_event_id: 91,
      source: 'netapp',
      event_code: 'secd.authsys.lookup.failed',
      association_type: 'fault_log',
      association_type_label: '故障日志',
      title_zh: '认证服务查询失败',
      description_zh: '名称服务或认证后端查询失败。',
      recommended_solution_zh: '检查认证后端和网络连通性。',
      review_status: 'reviewed',
      object_id: 'node-a',
      object_name: 'node-a',
      description: 'Unable to retrieve credentials',
    };
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
    incidentApi.fetchIncidents.mockResolvedValue({ content: [], total: 0 });
    storageClusterApi.exportAnalytics.mockResolvedValue({
      data: new Blob(['report']),
      headers: { 'content-disposition': 'attachment; filename="storage-health.xlsx"' },
    });
  });

  it('shows storage distribution beside capacity and loads capacity first', async () => {
    const wrapper = await mountPage();

    expect(wrapper.text()).toContain('容量趋势');
    expect(wrapper.text()).toContain('存储分布');
    expect(wrapper.text()).toContain('容量池');
    expect(wrapper.text()).toContain('存储空间');
    expect(wrapper.text()).toContain('Qtree（NetApp）');
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

  it('keeps Qtree unavailable for an Isilon cluster', async () => {
    storageClusterApi.fetchById.mockResolvedValue({ id: 42, name: 'cluster-a', storage_type: 'isilon' });

    const wrapper = await mountPage();

    expect(wrapper.text()).toContain('容量池');
    expect(wrapper.text()).toContain('存储空间');
    expect(wrapper.text()).not.toContain('Qtree（NetApp）');
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

  it('renders the shared time filter inside each time-based analysis tab content', async () => {
    storageClusterApi.fetchCapacityChange.mockResolvedValue({
      data: [{ updated_at: initialRange[0], used: 1 }],
      data_unit: 'TB',
      trend_meta: {
        quota_basis: 'hard',
        rule_source: 'system',
        thresholds: { important: 80, serious: 90, emergency: 95 },
        quota_limit_gb: 1000,
        quota_limit_tb: 0.9766,
        ratio_indicator: 'used_ratio',
      },
    });
    const wrapper = await mountPage();
    const tabs = wrapper.get('[data-testid="analytics-tabs"]');
    const filter = wrapper.get('[data-tab="capacity"] .storage-health-filter');
    const datePicker = filter.findComponent({ name: 'ElDatePicker' });

    expect(tabs.find('.storage-health-filter').exists()).toBe(true);
    expect(filter.exists()).toBe(true);
    expect(datePicker.attributes('format')).toBe('YYYY-MM-DD HH:mm:ss');
    expect(datePicker.attributes('start-placeholder')).toBe('开始日期时间');
    expect(datePicker.attributes('end-placeholder')).toBe('结束日期时间');
    expect(wrapper.findComponent({ name: 'StorageTrendChart' }).props()).toMatchObject({
      indicator: 'used',
      unit: 'TB',
      ariaLabel: '存储集群已使用容量趋势',
      height: '520px',
    });

    await selectTab(wrapper, 'performance');

    expect(wrapper.get('[data-tab="performance"] .storage-health-filter').exists()).toBe(true);
    expect(wrapper.get('[data-tab="performance"] .performance-limit').exists()).toBe(true);

    await selectTab(wrapper, 'faults');

    expect(wrapper.get('[data-tab="faults"] .storage-health-filter').exists()).toBe(true);

    await selectTab(wrapper, 'distribution');

    expect(wrapper.find('.storage-health-filter').exists()).toBe(false);
    expect(wrapper.findComponent({ name: 'DiskUsage' }).attributes('height')).toBe('100%');
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
      limit: 10,
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

  it('filters performance row count and shows multiple standardized metrics with p95 by default', async () => {
    storageClusterApi.fetchTopLatency.mockResolvedValue({
      supported: true,
      data: [
        {
          object_id: 'volume-1',
          object_name: 'vol-a',
          object_type: 'volume',
          p95_latency: 9.5,
          avg_latency: 5,
          max_latency: 12,
          avg_read_latency: 3,
          avg_write_latency: 7,
          avg_iops: 125,
          avg_throughput: 4096,
          sample_count: 8,
        },
        {
          object_id: 'volume-2',
          object_name: 'vol-b',
          object_type: 'volume',
          p95_latency: 3.5,
          avg_latency: 2,
          max_latency: 4,
          avg_read_latency: 1,
          avg_write_latency: 3,
          avg_iops: 88,
          avg_throughput: 2048,
          sample_count: 6,
        },
      ],
    });
    const wrapper = await mountPage();

    await selectTab(wrapper, 'performance');

    expect(storageClusterApi.fetchTopLatency).toHaveBeenLastCalledWith(42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
      object_type: 'volume',
      limit: 10,
    });
    expect(wrapper.get('.performance-limit').findComponent({ name: 'ElSelect' }).props('modelValue')).toBe(10);
    expect(wrapper.get('.performance-metrics').findComponent({ name: 'ElSelect' }).props('modelValue')).toEqual(['p95_latency']);
    expect(wrapper.get('.performance-objects').findComponent({ name: 'ElSelect' }).props('modelValue')).toEqual([]);
    expect(wrapper.findAllComponents({ name: 'BarStackChart' })).toHaveLength(1);
    expect(wrapper.findComponent({ name: 'BarStackChart' }).props()).toMatchObject({
      categories: ['vol-a', 'vol-b'],
      data: [[9.5, 3.5]],
      seriesNames: ['p95_latency'],
      unit: 'ms',
    });

    await wrapper.get('.performance-objects').findComponent({ name: 'ElSelect' })
      .vm.$emit('update:modelValue', ['volume-2']);
    await flushPromises();
    expect(wrapper.findComponent({ name: 'BarStackChart' }).props()).toMatchObject({
      categories: ['vol-b'],
      data: [[3.5]],
    });
    expect(wrapper.get('[data-tab="performance"]').findComponent({ name: 'ElTable' }).props('data'))
      .toEqual([expect.objectContaining({ object_id: 'volume-2' })]);

    await wrapper.get('.performance-metrics').findComponent({ name: 'ElSelect' })
      .vm.$emit('update:modelValue', ['p95_latency', 'avg_iops']);
    await flushPromises();
    expect(wrapper.findAllComponents({ name: 'BarStackChart' })).toHaveLength(2);

    await wrapper.get('.performance-limit').findComponent({ name: 'ElSelect' })
      .vm.$emit('update:modelValue', 50);
    await wrapper.get('.storage-health-filter').findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await flushPromises();
    expect(storageClusterApi.fetchTopLatency).toHaveBeenLastCalledWith(42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
      object_type: 'volume',
      limit: 50,
    });

    await wrapper.get('.storage-health-filter').findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await flushPromises();
    expect(wrapper.get('.performance-limit').findComponent({ name: 'ElSelect' }).props('modelValue')).toBe(10);
    expect(wrapper.get('.performance-metrics').findComponent({ name: 'ElSelect' }).props('modelValue')).toEqual(['p95_latency']);
    expect(wrapper.get('.performance-objects').findComponent({ name: 'ElSelect' }).props('modelValue')).toEqual([]);
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

  it('keeps event semantics compact and reveals association guidance on hover', async () => {
    storageClusterApi.fetchSystemEvents.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      data: [tableRow],
    });
    const wrapper = await mountPage();

    await selectTab(wrapper, 'faults');

    const eventSection = wrapper.get('.system-events');
    const columns = eventSection.findAllComponents({ name: 'ElTableColumn' });
    const associationColumn = columns.find((column) => column.attributes('label') === '关联类型');
    expect(associationColumn.attributes('min-width')).toBe('120');
    expect(eventSection.text()).toContain('认证服务查询失败');
    expect(eventSection.text()).toContain('secd.authsys.lookup.failed');
    expect(associationColumn.findAllComponents({ name: 'ElTag' }).map((tag) => tag.text()))
      .toEqual(['故障日志']);
    expect(associationColumn.text()).not.toContain('已审核');

    const tooltip = associationColumn.getComponent({ name: 'ElTooltip' });
    expect(tooltip.text()).toContain('关联提示');
    expect(tooltip.text()).toContain('名称服务或认证后端查询失败。');
    expect(tooltip.text()).toContain('采取措施');
    expect(tooltip.text()).toContain('检查认证后端和网络连通性。');
  });

  it('explains repeated event fingerprints and opens the normalized vendor log', async () => {
    storageClusterApi.fetchRepeatedFaults.mockResolvedValue({
      data: [{
        source: 'netapp',
        fingerprint: 'netapp:secd.authsys.lookup.failed:node:node-1',
        event_code: 'secd.authsys.lookup.failed',
        association_type: 'fault_log',
        association_type_label: '故障日志',
        title_zh: '认证服务查询失败',
        description_zh: '名称服务或认证后端查询失败，需要核对网络和目录服务。',
        sample_event_id: 91,
        log_excerpt: 'Unable to retrieve credentials',
        count: 3,
      }],
    });
    storageClusterApi.fetchSystemEventDetail.mockResolvedValue({
      id: 91,
      source: 'netapp',
      event_code: 'secd.authsys.lookup.failed',
      title_zh: '认证服务查询失败',
      association_type: 'fault_log',
      association_type_label: '故障日志',
      review_status: 'reviewed',
      recommended_solution_zh: '检查认证后端和网络连通性。',
      description: 'Unable to retrieve credentials for SVM_nas',
      fingerprint: 'netapp:secd.authsys.lookup.failed:node:node-1',
      object_name: 'node-a',
      occurred_at: '2026-07-14 18:54:00',
    });
    const wrapper = await mountPage();

    await selectTab(wrapper, 'faults');

    expect(wrapper.text()).toContain('认证服务查询失败');
    expect(wrapper.text()).toContain('故障日志');
    expect(wrapper.text()).toContain('Unable to retrieve credentials');
    expect(wrapper.text()).not.toContain('故障指纹 netapp:');

    await wrapper.get('[data-testid="repeated-event-log-91"]').trigger('click');
    await flushPromises();

    expect(storageClusterApi.fetchSystemEventDetail).toHaveBeenCalledWith(42, 91);
    expect(wrapper.text()).toContain('Unable to retrieve credentials for SVM_nas');
    expect(wrapper.text()).toContain('检查认证后端和网络连通性。');
    expect(wrapper.findComponent({ name: 'ElDialog' }).attributes('title')).toBe('事件日志详情');
  });

  it('keeps event log actions reachable and hides low-frequency columns on narrow screens', async () => {
    storageClusterApi.fetchErrorSeverity.mockResolvedValue({ total: 1, counts: { error: 1 } });
    storageClusterApi.fetchRepeatedFaults.mockResolvedValue({
      data: [{
        ...tableRow,
        count: 3,
        log_excerpt: 'Unable to retrieve credentials',
        first_occurred_at: '2026-07-21 08:06:21',
        last_occurred_at: '2026-07-21 09:06:21',
      }],
    });
    storageClusterApi.fetchSystemEvents.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      data: [tableRow],
    });
    const wrapper = await mountPage();

    await selectTab(wrapper, 'faults');

    const assertCompactColumn = (columns, label) => {
      const column = columns.find((candidate) => candidate.attributes('label') === label);
      expect(column, `${label} column`).toBeDefined();
      expect(column.attributes('class-name')).toContain('mobile-hidden');
      expect(column.attributes('class-name')).toContain('tablet-hidden');
      expect(column.attributes('label-class-name')).toContain('mobile-hidden');
      expect(column.attributes('label-class-name')).toContain('tablet-hidden');
    };

    const repeatedSection = wrapper.get('.fault-grid');
    const repeatedColumns = repeatedSection.findAllComponents({ name: 'ElTableColumn' });
    ['来源', '日志摘要', '首次发生'].forEach((label) => assertCompactColumn(repeatedColumns, label));
    const repeatedAction = repeatedColumns.find((column) => column.attributes('label') === '操作');
    expect(repeatedAction.attributes('fixed')).toBe('right');
    expect(repeatedAction.find('.list-row-actions').exists()).toBe(true);

    const systemEventSection = wrapper.get('.system-events');
    const systemEventColumns = systemEventSection.findAllComponents({ name: 'ElTableColumn' });
    ['来源', '事件对象', '内容'].forEach((label) => assertCompactColumn(systemEventColumns, label));
    const systemEventAction = systemEventColumns.find((column) => column.attributes('label') === '操作');
    expect(systemEventAction.attributes('fixed')).toBe('right');
    expect(systemEventAction.find('.list-row-actions').exists()).toBe(true);
  });

  it('keeps pending or unknown vendor semantics visibly unclassified in the list and detail', async () => {
    tableRow = {
      ...tableRow,
      association_type: 'unknown',
      association_type_label: '候选故障日志',
      title_zh: '候选磁盘故障',
      description_zh: '候选说明不应作为正式故障结论。',
      review_status: 'pending',
    };
    storageClusterApi.fetchSystemEvents.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      data: [tableRow],
    });
    storageClusterApi.fetchSystemEventDetail.mockResolvedValue({
      ...tableRow,
      description: 'disk bay 4 reported an unclassified vendor event',
      fingerprint: 'netapp:test.vendor.event:disk:4',
      occurred_at: '2026-07-21 09:06:21',
    });
    const wrapper = await mountPage();

    await selectTab(wrapper, 'faults');

    const eventSection = wrapper.get('.system-events');
    expect(eventSection.find('strong').text()).toBe('待审核 · 未分类厂商事件');
    expect(eventSection.findAllComponents({ name: 'ElTag' }).map((tag) => tag.text()))
      .toEqual(['未分类厂商事件']);

    await eventSection.findComponent({ name: 'TableActionButton' }).trigger('click');
    await flushPromises();

    const detail = wrapper.get('.system-event-detail');
    expect(detail.text()).toContain('待审核');
    expect(detail.text()).toContain('未分类厂商事件');
    expect(detail.text()).toContain('该事件代码尚未完成审核');
    expect(detail.text()).toContain('暂无可核验官方方案');
    expect(detail.text()).toContain('disk bay 4 reported an unclassified vendor event');
    expect(detail.text()).not.toContain('候选磁盘故障');
    expect(detail.text()).not.toContain('候选说明不应作为正式故障结论');
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

    await eventFilter.vm.$emit('reset');
    await flushPromises();
    expect(storageClusterApi.fetchSystemEvents).toHaveBeenLastCalledWith(42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
      page: 1,
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
    const dropdown = () => wrapper.findComponent({ name: 'ElDropdown' });

    await dropdown().vm.$emit('command', 'current:csv');
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
    await dropdown().vm.$emit('command', 'current:pdf');
    await flushPromises();
    expect(storageClusterApi.exportAnalytics).toHaveBeenNthCalledWith(2, 42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
      section: 'latency',
      format: 'pdf',
    });

    await selectTab(wrapper, 'faults');
    await dropdown().vm.$emit('command', 'severity:csv');
    await flushPromises();
    expect(storageClusterApi.exportAnalytics).toHaveBeenNthCalledWith(3, 42, {
      start_time: initialRange[0],
      end_time: initialRange[1],
      section: 'severity',
      format: 'csv',
    });

    await dropdown().vm.$emit('command', 'all:excel');
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

  it('uses the shared data table without page-level table style overrides', () => {
    expect(storageClusterDetailSource.match(/<DataTable\b/g)).toHaveLength(3);
    expect(storageClusterDetailSource).not.toMatch(/<ElTable\b|<ElPagination\b/);
    expect(storageClusterDetailSource).not.toMatch(/\.table-wrap\b|:deep\(\.el-table/);
  });

  it('allows tab panes to shrink so fixed log actions remain reachable on narrow screens', () => {
    expect(storageClusterDetailSource).toMatch(
      /\.storage-health-page__tabs :deep\(\.el-tab-pane\)\s*\{[^}]*min-width:\s*0;/s,
    );
  });
});
