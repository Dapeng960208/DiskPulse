import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  groupApi: { fetch: vi.fn(), deleteById: vi.fn(), fetchStorageRealTimeDataById: vi.fn() },
  groupTagApi: { fetch: vi.fn(), deleteById: vi.fn() },
  storageUsageApi: { fetch: vi.fn(), exportStorageUsages: vi.fn(), fetchStorageRealTimeDataById: vi.fn() },
  qtreeApi: { fetchStorageRealTimeDataById: vi.fn() },
  volumeApi: { fetchStorageRealTimeDataById: vi.fn() },
  projectApi: { fetchStorageRealTimeDataById: vi.fn() },
  alertApi: { fetch: vi.fn() },
  usersApi: { fetch: vi.fn(), deleteById: vi.fn(), syncLdap: vi.fn() },
  storageClusterApi: {
    fetchById: vi.fn(),
    fetchCapacityChange: vi.fn(),
    fetchTopLatency: vi.fn(),
    fetchErrorSeverity: vi.fn(),
    fetchRepeatedFaults: vi.fn(),
    fetchSystemEvents: vi.fn(),
    exportAnalytics: vi.fn(),
  },
  aggregateApi: { fetchAggregateTrees: vi.fn(), fetchStorageRealTimeDataById: vi.fn() },
  routerPush: vi.fn(),
  route: { query: {}, params: { id: '42' } },
  confirm: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
  hasRole: vi.fn(),
  exportReport: vi.fn(),
  currentUser: { extensionAttributes: { rdUsername: null } },
  GroupFormDialogedit: vi.fn(),
  QuotaAdjustmentDialogopen: vi.fn(),
  UsageFormDialogedit: vi.fn(),
  ExportDialogopen: vi.fn(),
  UserFormDialogedit: vi.fn(),
  GroupTagFormDialogedit: vi.fn(),
}));

vi.mock('@/api/group-api.js', () => ({ default: mocks.groupApi }));
vi.mock('@/api/group-tag-api', () => ({ default: mocks.groupTagApi }));
vi.mock('@/api/storage-usage-api.js', () => ({ default: mocks.storageUsageApi }));
vi.mock('@/api/qtree-api.js', () => ({ default: mocks.qtreeApi }));
vi.mock('@/api/volume-api', () => ({ default: mocks.volumeApi }));
vi.mock('@/api/project-api.js', () => ({ default: mocks.projectApi }));
vi.mock('@/api/alert-api.js', () => ({ default: mocks.alertApi }));
vi.mock('@/api/users-api', () => ({ default: mocks.usersApi }));
vi.mock('@/api/storage-cluster-api', () => ({ default: mocks.storageClusterApi }));
vi.mock('@/api/aggregate-api.js', () => ({ default: mocks.aggregateApi }));
vi.mock('@/utils/authorization', () => ({ hasRole: mocks.hasRole }));
vi.mock('@/utils/common.js', () => ({ exportReport: mocks.exportReport }));
vi.mock('@/stores/current-user', () => ({ useCurrentUser: () => mocks.currentUser }));
vi.mock('@/stores/storage-alert-thresholds', () => ({
  useStorageAlertThresholds: () => ({
    thresholds: { important: 80, serious: 90, emergency: 95 },
    load: vi.fn(),
  }),
}));
vi.mock('@/composables/common', () => ({ getDefaultTime: () => ['2026-07-01 00:00:00', '2026-07-02 00:00:00'] }));
vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal()),
  useRouter: () => ({ push: mocks.routerPush }),
  useRoute: () => mocks.route,
}));
vi.mock('element-plus', async (importOriginal) => ({
  ...(await importOriginal()),
  ElMessageBox: { confirm: mocks.confirm },
  ElMessage: { success: mocks.success, error: mocks.error },
}));

const { default: GroupListPage } = await import('@/pages/group/GroupListPage.vue');
const { default: GroupTagListPage } = await import('@/pages/group-tag/GroupTagListPage.vue');
const { default: UsageListPage } = await import('@/pages/usage/UsageListPage.vue');
const { default: RealTimePage } = await import('@/pages/common/RealTimePage.vue');
const { default: AlertListPage } = await import('@/pages/alert/AlertListPage.vue');
const { default: StorageClusterDetailPage } = await import('@/pages/admin/storage-cluster/StorageClusterDetailPage.vue');
const { default: UserListPage } = await import('@/pages/admin/user/UserListPage.vue');

const row = {
  id: 9,
  name: 'group-a',
  rd_username: 'alice',
  username: 'Alice',
  email: 'alice@example.com',
  department: '研发部',
  user_type: 2,
  is_alert: true,
  storage_used: 2048,
  used: 2048,
  limit: 4096,
  soft_limit: 1024,
  linux_path: '/data/alice',
  project: { id: 1, name: '项目 A' },
  group: { id: 2, name: '项目组 A' },
  group_tag: { id: 3, name: '标签 A' },
  user: { rd_username: 'alice', user_type: 2 },
  storage_cluster: { id: 4, name: '集群 A', storage_type: 'NetApp' },
  storage_target: { type: 'volume', name: '卷 A' },
  in_charge_user: { rd_username: 'owner', username: 'Owner', avatar_url: '' },
  associate_multiple_groups: false,
  capabilities: { adjust_quota: true },
};

let tableRows = [row];
const mountedWrappers = [];

const passthrough = (name, tag = 'div') => defineComponent({
  name,
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    return () => h(tag, attrs, slots.default?.());
  },
});

const FilterForm = defineComponent({
  name: 'FilterForm',
  emits: ['query', 'reset', 'export'],
  setup(_, { slots }) {
    return () => h('form', { 'data-testid': 'filter-form' }, [
      ...(slots.default?.() || []),
      ...(slots.advanced?.() || []),
      ...(slots['active-filters']?.() || []),
      ...(slots.actions?.() || []),
    ]);
  },
});

const Button = defineComponent({
  name: 'ElButton',
  props: { disabled: Boolean, loading: Boolean },
  emits: ['click'],
  setup(props, { attrs, emit, slots }) {
    return () => h('button', {
      ...attrs,
      type: attrs.type || 'button',
      disabled: props.disabled || props.loading,
      onClick: () => emit('click'),
    }, slots.default?.());
  },
});

const Input = defineComponent({
  name: 'ElInput',
  props: { modelValue: { type: [String, Number], default: '' }, placeholder: String },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('input', {
      value: props.modelValue,
      placeholder: props.placeholder,
      onInput: (event) => emit('update:modelValue', event.target.value),
    });
  },
});

const Select = defineComponent({
  name: 'ElSelect',
  props: { modelValue: { type: [String, Number, Array], default: '' } },
  emits: ['update:modelValue'],
  setup(props, { attrs, emit, slots }) {
    return () => h('select', {
      ...attrs,
      value: props.modelValue,
      onChange: (event) => emit('update:modelValue', event.target.value),
    }, slots.default?.());
  },
});

const DatePicker = defineComponent({
  name: 'ElDatePicker',
  props: { modelValue: { type: Array, default: () => [] } },
  emits: ['update:modelValue'],
  setup() {
    return () => h('input', { 'data-testid': 'date-range' });
  },
});

const Selectable = (name) => defineComponent({
  name,
  props: { modelValue: { type: [String, Number, Array], default: null } },
  emits: ['update:modelValue', 'selected-label-change'],
  setup(props, { emit }) {
    return () => h('select', {
      value: props.modelValue,
      onChange: (event) => emit('update:modelValue', event.target.value),
    });
  },
});

const Tag = defineComponent({
  name: 'ElTag',
  props: { closable: Boolean, type: String },
  emits: ['close'],
  setup(props, { emit, slots }) {
    return () => h('span', { 'data-closable': props.closable ? 'true' : undefined }, [
      ...(slots.default?.() || []),
      props.closable ? h('button', { type: 'button', 'aria-label': '关闭筛选', onClick: () => emit('close') }, '×') : null,
    ]);
  },
});

const TableColumn = defineComponent({
  name: 'ElTableColumn',
  props: { label: String },
  setup(props, { slots }) {
    return () => h('div', { 'data-column': props.label || '' }, [
      ...(slots.header?.() || []),
      ...tableRows.flatMap((tableRow) => slots.default?.({ row: tableRow }) || []),
    ]);
  },
});

const DataTable = defineComponent({
  name: 'DataTable',
  props: { pagination: Object, loading: Boolean, data: Array },
  emits: ['update:pagination'],
  setup(_, { slots }) {
    return () => h('section', { 'data-testid': 'data-table' }, slots.default?.());
  },
});

const Dropdown = defineComponent({
  name: 'ElDropdown',
  setup(_, { slots }) {
    return () => h('div', slots.default?.().concat(slots.dropdown?.() || []));
  },
});

const DropdownItem = defineComponent({
  name: 'ElDropdownItem',
  props: { disabled: Boolean },
  emits: ['click'],
  setup(props, { attrs, emit, slots }) {
    return () => h('button', {
      ...attrs,
      disabled: props.disabled,
      onClick: () => emit('click'),
    }, slots.default?.());
  },
});

const Tabs = defineComponent({
  name: 'ElTabs',
  props: { modelValue: { type: String, default: '' } },
  emits: ['update:modelValue'],
  setup(_, { slots }) {
    return () => h('div', { 'data-testid': 'tabs' }, slots.default?.());
  },
});

const TabPane = defineComponent({
  name: 'ElTabPane',
  props: { name: String, label: String },
  setup(props, { slots }) {
    return () => h('section', { 'data-tab': props.name }, [props.label, ...(slots.default?.() || [])]);
  },
});

const Pagination = defineComponent({
  name: 'ElPagination',
  props: { currentPage: Number, pageSize: Number, total: Number },
  emits: ['current-change', 'size-change'],
  setup(_, { slots }) {
    return () => h('nav', slots.default?.());
  },
});

const Table = defineComponent({
  name: 'ElTable',
  props: { data: { type: Array, default: () => [] } },
  setup(props, { slots }) {
    return () => h('div', { 'data-testid': 'el-table' }, [
      JSON.stringify(props.data),
      ...(slots.default?.() || []),
    ]);
  },
});

const DialogStub = (name, methods) => defineComponent({
  name,
  setup(_, { expose }) {
    expose(Object.fromEntries(methods.map((method) => [method, mocks[`${name}${method}`] || vi.fn()])));
    return () => h('div');
  },
});

const dialogStubs = {
  GroupFormDialog: DialogStub('GroupFormDialog', ['edit']),
  QuotaAdjustmentDialog: DialogStub('QuotaAdjustmentDialog', ['open']),
  UsageFormDialog: DialogStub('UsageFormDialog', ['edit']),
  ExportDialog: DialogStub('ExportDialog', ['open']),
  UserFormDialog: DialogStub('UserFormDialog', ['edit']),
  GroupTagFormDialog: DialogStub('GroupTagFormDialog', ['edit']),
};

const commonStubs = {
  FilterForm,
  QueryForm: FilterForm,
  DataTable,
  ElButton: Button,
  ElDropdown: Dropdown,
  ElDropdownItem: DropdownItem,
  ElDropdownMenu: passthrough('ElDropdownMenu'),
  ElFormItem: passthrough('ElFormItem'),
  ElInput: Input,
  ElSelect: Select,
  ElOption: passthrough('ElOption', 'option'),
  ElTag: Tag,
  ElTableColumn: TableColumn,
  ElTable: Table,
  ElDatePicker: DatePicker,
  ElCard: passthrough('ElCard'),
  ElDescriptions: passthrough('ElDescriptions'),
  ElDescriptionsItem: passthrough('ElDescriptionsItem'),
  ElTabs: Tabs,
  ElTabPane: TabPane,
  ElPagination: Pagination,
  RouterLink: passthrough('RouterLink', 'a'),
  GroupTagSelect: Selectable('GroupTagSelect'),
  ProjectSelect: Selectable('ProjectSelect'),
  StorageClusterSelect: Selectable('StorageClusterSelect'),
  VolumeSelect: Selectable('VolumeSelect'),
  QtreeSelect: Selectable('QtreeSelect'),
  GroupSelect: Selectable('GroupSelect'),
  RdUserSelect: Selectable('RdUserSelect'),
  StorageUsageSelect: Selectable('StorageUsageSelect'),
  AggregateSelect: Selectable('AggregateSelect'),
  UserAvatar: passthrough('UserAvatar'),
  Progress: passthrough('Progress'),
  StorageTrendChart: defineComponent({
    name: 'StorageTrendChart',
    props: { series: Array, indicator: String, trendMeta: Object, systemThresholds: Object, unit: String, ariaLabel: String },
    template: '<div class="storage-trend-chart-stub" />',
  }),
  AnimatedTextChart: passthrough('AnimatedTextChart'),
  LoadingCharts: passthrough('LoadingCharts'),
  DiskUsage: passthrough('DiskUsage'),
  PieCharts: passthrough('PieCharts'),
  BarStackChart: passthrough('BarStackChart'),
  ...dialogStubs,
};

const mountPage = async (component, options = {}) => {
  const wrapper = shallowMount(component, {
    attachTo: document.body,
    ...options,
    global: {
      plugins: [createPinia()],
      stubs: { ...commonStubs, ...(options.global?.stubs || {}) },
      directives: { loading: () => {}, ...(options.global?.directives || {}) },
    },
  });
  mountedWrappers.push(wrapper);
  await flushPromises();
  return wrapper;
};

const findButton = (wrapper, text) => wrapper.findAll('button').find((button) => button.text().includes(text));
const closeFilterTag = async (wrapper, text) => {
  await flushPromises();
  const tag = wrapper.findAllComponents({ name: 'ElTag' })
    .find((candidate) => candidate.props('closable') && candidate.text().includes(text));
  await tag.find('button').trigger('click');
  await flushPromises();
};
const query = (api) => expect(api.fetch).toHaveBeenCalled();

beforeEach(() => {
  tableRows = [row];
  mocks.route.query = {};
  mocks.route.params = { id: '42' };
  mocks.currentUser.extensionAttributes = { rdUsername: null };
  mocks.hasRole.mockReturnValue(true);
  mocks.confirm.mockResolvedValue(undefined);
  mocks.groupApi.fetch.mockResolvedValue({ content: [row], total: 1 });
  mocks.groupApi.deleteById.mockResolvedValue({});
  mocks.groupTagApi.fetch.mockResolvedValue({ content: [row], total: 1 });
  mocks.groupTagApi.deleteById.mockResolvedValue({});
  mocks.storageUsageApi.fetch.mockResolvedValue({ content: [row], total: 1 });
  mocks.storageUsageApi.exportStorageUsages.mockResolvedValue({ data: new Blob(['usage']), headers: { filename: 'usage.xlsx' } });
  mocks.storageUsageApi.fetchStorageRealTimeDataById.mockResolvedValue({
    info: { linux_path: '/data/a', limit: 100, used: 20, use_ratio: 20 },
    data: [],
    trend_meta: { quota_basis: 'hard', rule_source: 'system', thresholds: { important: 80, serious: 90, emergency: 95 }, quota_limit_gb: 100, ratio_indicator: 'used_ratio' },
  });
  mocks.qtreeApi.fetchStorageRealTimeDataById.mockResolvedValue({ info: { name: 'qtree-a', limit: 100, used: 20, use_ratio: 20 }, data: [] });
  mocks.volumeApi.fetchStorageRealTimeDataById.mockResolvedValue({ info: { name: 'volume-a', limit: 100, used: 20, use_ratio: 20 }, data: [] });
  mocks.projectApi.fetchStorageRealTimeDataById.mockResolvedValue({ info: { name: 'project-a', limit: 100, used: 20, use_ratio: 20 }, data: [] });
  mocks.alertApi.fetch.mockResolvedValue({ content: [] });
  mocks.usersApi.fetch.mockResolvedValue({ content: [row], total: 1 });
  mocks.usersApi.deleteById.mockResolvedValue({});
  mocks.usersApi.syncLdap.mockResolvedValue({ ldap_total: 1, created: 1, updated: 0, reactivated: 0, marked_inactive: 0 });
  mocks.storageClusterApi.fetchById.mockResolvedValue({ id: 42, name: 'cluster-a' });
  mocks.storageClusterApi.fetchCapacityChange.mockResolvedValue({ data: [] });
  mocks.storageClusterApi.fetchTopLatency.mockResolvedValue({ supported: true, data: [] });
  mocks.storageClusterApi.fetchErrorSeverity.mockResolvedValue({ total: 0, counts: {} });
  mocks.storageClusterApi.fetchRepeatedFaults.mockResolvedValue({ data: [] });
  mocks.storageClusterApi.fetchSystemEvents.mockResolvedValue({ data: [], total: 0, page: 1, page_size: 20 });
  mocks.storageClusterApi.exportAnalytics.mockResolvedValue({ data: new Blob(['report']), headers: {} });
  mocks.aggregateApi.fetchAggregateTrees.mockResolvedValue({ data: [] });
  mocks.aggregateApi.fetchStorageRealTimeDataById.mockResolvedValue({ info: { name: 'aggregate-a', limit: 100, used: 20, use_ratio: 20 }, data: [] });
  mocks.exportReport.mockReset();
});

afterEach(() => {
  mountedWrappers.splice(0).forEach((wrapper) => wrapper.unmount());
});

describe('list page coverage gaps', () => {
  it('filters, resets, paginates, and executes group actions through the page UI', async () => {
    const wrapper = await mountPage(GroupListPage);
    const project = wrapper.findComponent({ name: 'ProjectSelect' });
    const cluster = wrapper.findComponent({ name: 'StorageClusterSelect' });
    const volume = wrapper.findComponent({ name: 'VolumeSelect' });
    const qtree = wrapper.findComponent({ name: 'QtreeSelect' });

    await project.vm.$emit('update:modelValue', 7);
    await cluster.vm.$emit('update:modelValue', 8);
    await volume.vm.$emit('update:modelValue', 9);
    await volume.vm.$emit('selected-label-change', '卷 A');
    await qtree.vm.$emit('update:modelValue', 10);
    await qtree.vm.$emit('selected-label-change', 'Qtree A');
    await wrapper.findComponent({ name: 'GroupTagSelect' }).vm.$emit('update:modelValue', 11);
    await wrapper.findComponent({ name: 'GroupTagSelect' }).vm.$emit('selected-label-change', '标签 A');

    await wrapper.findComponent({ name: 'DataTable' }).vm.$emit('update:pagination', {
      page: 3,
      pageSize: 50,
      prop: 'name',
      order: 'ascending',
    });
    await flushPromises();
    expect(mocks.groupApi.fetch).toHaveBeenLastCalledWith(expect.objectContaining({
      project_id: 7,
      storage_cluster_id: 8,
      qtree_id: 10,
      volume_id: null,
      page: 3,
      size: 50,
      prop: 'name',
      order: 'ascending',
    }));

    await closeFilterTag(wrapper, '项目组标签');
    await closeFilterTag(wrapper, '关联 Qtree');
    await wrapper.findComponent({ name: 'VolumeSelect' }).vm.$emit('update:modelValue', 12);
    await wrapper.findComponent({ name: 'VolumeSelect' }).vm.$emit('selected-label-change', '卷 B');
    await closeFilterTag(wrapper, '关联存储空间');
    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await flushPromises();
    expect(mocks.groupApi.fetch).toHaveBeenLastCalledWith({ page: 1, size: 20 });

    await findButton(wrapper, '添加项目组').trigger('click');
    await findButton(wrapper, '详情').trigger('click');
    await findButton(wrapper, '调整配额').trigger('click');
    await findButton(wrapper, '编辑').trigger('click');
    await findButton(wrapper, '删除').trigger('click');
    const deleteOptions = mocks.confirm.mock.calls.at(-1)?.[2];
    const done = vi.fn();
    await deleteOptions.beforeClose('confirm', { confirmButtonLoading: false }, done);
    await flushPromises();
    expect(mocks.groupApi.deleteById).toHaveBeenCalledWith(9);
    expect(done).toHaveBeenCalled();
    expect(mocks.routerPush).toHaveBeenCalledWith({ path: '/group/9' });
    expect(mocks.GroupFormDialogedit).toHaveBeenCalled();
    expect(mocks.QuotaAdjustmentDialogopen).toHaveBeenCalledWith(row);
  });

  it('keeps admin-only group and usage actions hidden without permission', async () => {
    mocks.hasRole.mockReturnValue(false);
    tableRows = [{ ...row, capabilities: { adjust_quota: false } }];
    const groupWrapper = await mountPage(GroupListPage);
    const usageWrapper = await mountPage(UsageListPage);

    expect(findButton(groupWrapper, '添加项目组')).toBeUndefined();
    expect(findButton(usageWrapper, '新增')).toBeUndefined();
    expect(findButton(groupWrapper, '调整配额')).toBeUndefined();
    expect(findButton(usageWrapper, '调整配额')).toBeUndefined();
  });

  it('filters, exports, resets, paginates, and executes usage actions through the page UI', async () => {
    mocks.currentUser.extensionAttributes = { rdUsername: 'alice' };
    const wrapper = await mountPage(UsageListPage);
    expect(mocks.storageUsageApi.fetch).toHaveBeenCalledWith(expect.objectContaining({ nameLike: 'alice' }));

    await wrapper.findComponent({ name: 'ProjectSelect' }).vm.$emit('update:modelValue', 7);
    await wrapper.findComponent({ name: 'GroupTagSelect' }).vm.$emit('update:modelValue', 8);
    await wrapper.findComponent({ name: 'GroupTagSelect' }).vm.$emit('selected-label-change', '标签 A');
    await wrapper.findComponent({ name: 'GroupSelect' }).vm.$emit('update:modelValue', 9);
    await wrapper.findComponent({ name: 'GroupSelect' }).vm.$emit('selected-label-change', '项目组 A');
    await wrapper.findComponent({ name: 'ElInput' }).vm.$emit('update:modelValue', '/data');
    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await wrapper.findComponent({ name: 'DataTable' }).vm.$emit('update:pagination', {
      page: 2,
      pageSize: 50,
      prop: 'used',
      order: 'descending',
    });
    await flushPromises();
    expect(mocks.storageUsageApi.fetch).toHaveBeenLastCalledWith(expect.objectContaining({
      project_id: 7,
      group_tag_id: 8,
      group_id: 9,
      nameLike: '/data',
      page: 2,
      size: 50,
      prop: 'used',
      order: 'descending',
    }));

    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('export');
    expect(wrapper.findComponent({ name: 'ExportDialog' }).exists()).toBe(true);
    await wrapper.findComponent({ name: 'ExportDialog' }).vm.$emit('submitted', 'excel');
    expect(mocks.exportReport).toHaveBeenCalledWith(expect.any(Promise));

    await findButton(wrapper, '新增').trigger('click');
    await findButton(wrapper, '详情').trigger('click');
    await findButton(wrapper, '调整配额').trigger('click');
    expect(mocks.UsageFormDialogedit).toHaveBeenCalled();
    expect(mocks.QuotaAdjustmentDialogopen).toHaveBeenCalledWith(row);
    expect(mocks.routerPush).toHaveBeenCalledWith({ path: '/usage/9' });

    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await flushPromises();
    expect(mocks.storageUsageApi.fetch).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, size: 20 }));
  });

});

describe('group tag page coverage gaps', () => {
  it('queries, resets, paginates, edits, creates, and handles delete outcomes', async () => {
    const wrapper = await mountPage(GroupTagListPage);
    expect(mocks.groupTagApi.fetch).toHaveBeenCalledWith({ page: 1, size: 20, nameLike: null });

    await wrapper.findComponent({ name: 'ElInput' }).vm.$emit('update:modelValue', 'team');
    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await wrapper.findComponent({ name: 'DataTable' }).vm.$emit('update:pagination', { page: 2, pageSize: 50 });
    await flushPromises();
    expect(mocks.groupTagApi.fetch).toHaveBeenLastCalledWith({ page: 2, size: 50, nameLike: 'team' });

    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await flushPromises();
    expect(mocks.groupTagApi.fetch).toHaveBeenLastCalledWith({ page: 1, size: 20, nameLike: null });

    await findButton(wrapper, '新增标签').trigger('click');
    await findButton(wrapper, '编辑').trigger('click');
    expect(mocks.GroupTagFormDialogedit).toHaveBeenNthCalledWith(1);
    expect(mocks.GroupTagFormDialogedit).toHaveBeenNthCalledWith(2, row);

    await findButton(wrapper, '删除').trigger('click');
    await flushPromises();
    expect(mocks.groupTagApi.deleteById).toHaveBeenCalledWith(9);
    expect(mocks.success).toHaveBeenCalledWith('删除成功');

    mocks.confirm.mockRejectedValueOnce({ response: { status: 409 } });
    await findButton(wrapper, '删除').trigger('click');
    await flushPromises();
    expect(mocks.error).toHaveBeenCalledWith('该标签仍被项目组使用，不能删除');

    mocks.confirm.mockRejectedValueOnce(new Error('delete failed'));
    await findButton(wrapper, '删除').trigger('click');
    await flushPromises();
    expect(mocks.error).toHaveBeenCalledWith('删除失败，请稍后重试');

    mocks.confirm.mockRejectedValueOnce('cancel');
    await findButton(wrapper, '删除').trigger('click');
    await flushPromises();
    expect(mocks.error).not.toHaveBeenCalledWith('取消删除');
  });
});

describe('alert and user page coverage gaps', () => {
  it('renders alert display branches and handles query, reset, related type, and pagination events', async () => {
    tableRows = [
      {
        alert_type: 'alert', related_type: 'StorageUsage', event_type: 'trigger', alert_level: 'high',
        avg_use_ratio: 12.345, cluster_name: '集群 A', project_name: '项目 A',
        related_info: { context: { linux_path: '/data/a', username: 'alice' } },
      },
      {
        alert_type: 'alert', related_type: 'Group', event_type: 'recovery', alert_level: 'important',
        related_info: { context: { group: '项目组 A' } },
      },
      { alert_type: 'report', description: '周报内容', delivery_status: 'sent' },
      { alert_type: 'vendor_event', alert_level: 'unknown', description: '系统事件' },
      { alert_type: 'unknown', related_type: 'Unknown', event_type: 'unknown', description: '原始内容' },
    ];
    mocks.alertApi.fetch.mockResolvedValue({ content: tableRows, total: 5 });
    const wrapper = await mountPage(AlertListPage);
    expect(wrapper.text()).toContain('Linux目录 /data/a 首次告警（使用率 12.35%）');
    expect(wrapper.text()).toContain('项目组 项目组 A 恢复通知');
    expect(wrapper.text()).toContain('周报内容');
    expect(wrapper.text()).toContain('系统事件');
    expect(wrapper.text()).toContain('原始内容');

    const selects = wrapper.findAllComponents({ name: 'ElSelect' });
    await selects[1].vm.$emit('update:modelValue', 'Group');
    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await wrapper.findComponent({ name: 'DataTable' }).vm.$emit('update:pagination', {
      page: 4, pageSize: 50, prop: 'updated_at', order: 'descending',
    });
    await flushPromises();
    expect(mocks.alertApi.fetch).toHaveBeenLastCalledWith(expect.objectContaining({
      related_type: 'Group', page: 4, size: 50, prop: 'updated_at', order: 'descending',
    }));

    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await flushPromises();
    expect(mocks.alertApi.fetch).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, size: 20 }));
  });

  it('handles user route filters, pagination, edit, delete, reset, and LDAP cancellation', async () => {
    mocks.route.query = { nameLike: 'route-user' };
    const wrapper = await mountPage(UserListPage);
    expect(mocks.usersApi.fetch).toHaveBeenCalledWith(expect.objectContaining({ nameLike: 'route-user' }));

    await wrapper.findComponent({ name: 'ElInput' }).vm.$emit('update:modelValue', 'alice');
    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await wrapper.findComponent({ name: 'DataTable' }).vm.$emit('update:pagination', {
      page: 2, pageSize: 50, prop: 'username', order: 'ascending',
    });
    await flushPromises();
    expect(mocks.usersApi.fetch).toHaveBeenLastCalledWith(expect.objectContaining({
      nameLike: 'alice', page: 2, size: 50, prop: 'username', order: 'ascending',
    }));

    await findButton(wrapper, '新增用户').trigger('click');
    await findButton(wrapper, '编辑').trigger('click');
    expect(mocks.UserFormDialogedit).toHaveBeenCalledWith(row);

    await findButton(wrapper, '删除').trigger('click');
    const deleteOptions = mocks.confirm.mock.calls.at(-1)?.[2];
    const done = vi.fn();
    await deleteOptions.beforeClose('confirm', { confirmButtonLoading: false }, done);
    await flushPromises();
    expect(mocks.usersApi.deleteById).toHaveBeenCalledWith(9);
    expect(mocks.success).toHaveBeenCalledWith('删除成功');
    expect(done).toHaveBeenCalled();

    mocks.confirm.mockRejectedValueOnce(new Error('cancelled'));
    await findButton(wrapper, '同步LDAP').trigger('click');
    await flushPromises();
    expect(mocks.usersApi.syncLdap).not.toHaveBeenCalled();
    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await flushPromises();
    expect(mocks.usersApi.fetch).toHaveBeenLastCalledWith({ page: 1, size: 20, nameLike: null });
  });
});

describe('real-time page coverage gaps', () => {
  it('removes the duplicate header range and shows alert urgency instead of the prompt', async () => {
    tableRows = [
      { alert_level: 'emergency', avg_use_ratio: 96, updated_at: '2026-07-17' },
      { alert_level: 'important', avg_use_ratio: 82, updated_at: '2026-07-16' },
    ];
    mocks.alertApi.fetch.mockResolvedValueOnce({ content: tableRows });

    const wrapper = await mountPage(RealTimePage, {
      props: { apiType: 'storage-usage', label: '用户目录', attributeId: [1] },
    });

    expect(wrapper.find('.real-time-page__header > span').exists()).toBe(false);
    expect(wrapper.find('[data-column="提示"]').exists()).toBe(false);
    expect(wrapper.find('[data-column="告警紧急程度"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('紧急');
    expect(wrapper.text()).toContain('重要');
  });

  it('loads storage usage data, alerts, indicator changes, range reset, and multi-target charts', async () => {
    mocks.storageUsageApi.fetchStorageRealTimeDataById
      .mockResolvedValueOnce({ info: { linux_path: '/data/a', limit: 100, used: 20, use_ratio: 20 }, data: [['2026-07-17', 20]], trend_meta: { quota_basis: 'hard', rule_source: 'system', thresholds: { important: 80, serious: 90, emergency: 95 }, quota_limit_gb: 100, ratio_indicator: 'used_ratio' } })
      .mockResolvedValueOnce({ info: { linux_path: '/data/b', limit: 200, used: 40, use_ratio: 20 }, data: [['2026-07-17', 40]], trend_meta: { quota_basis: 'hard', rule_source: 'system', thresholds: { important: 80, serious: 90, emergency: 95 }, quota_limit_gb: 200, ratio_indicator: 'used_ratio' } });
    mocks.alertApi.fetch.mockResolvedValueOnce({ content: [
      { updated_at: '2026-07-02', description: 'new' },
      { updated_at: '2026-07-01', description: 'old' },
    ] });
    const wrapper = await mountPage(RealTimePage, {
      props: { apiType: 'storage-usage', label: '用户目录', attributeId: [1] },
    });

    expect(wrapper.text()).toContain('/data/a');
    expect(wrapper.findComponent({ name: 'StorageUsageSelect' }).exists()).toBe(true);
    expect(wrapper.findComponent({ name: 'StorageTrendChart' }).props()).toMatchObject({
      indicator: 'used',
      ariaLabel: '用户目录容量趋势',
    });
    expect(wrapper.findComponent({ name: 'ElTable' }).props('data')).toEqual([
      { updated_at: '2026-07-02', description: 'new' },
      { updated_at: '2026-07-01', description: 'old' },
    ]);

    await wrapper.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'alert_ratio');
    await wrapper.findComponent({ name: 'StorageUsageSelect' }).vm.$emit('update:modelValue', [1, 2]);
    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await wrapper.findComponent({ name: 'ElDatePicker' }).vm.$emit('update:modelValue', ['2026-07-03', '2026-07-04']);
    await flushPromises();
    expect(mocks.storageUsageApi.fetchStorageRealTimeDataById).toHaveBeenCalledWith(2, expect.objectContaining({ indicator: 'used' }));
    expect(mocks.storageUsageApi.fetchStorageRealTimeDataById).toHaveBeenCalledWith(1, expect.objectContaining({ indicator: 'alert_ratio' }));
    expect(mocks.storageUsageApi.fetchStorageRealTimeDataById).toHaveBeenCalled();
  });

  it('uses the non-storage realtime path and reacts to a changed attribute id', async () => {
    mocks.groupApi.fetchStorageRealTimeDataById.mockResolvedValue({
      info: { name: 'group-a', limit: 100, used: 25, use_ratio: 25 }, data: [{ value: 1 }],
    });
    const wrapper = await mountPage(RealTimePage, {
      props: { apiType: 'group', label: '项目组', attributeId: 3 },
    });
    expect(wrapper.findComponent({ name: 'GroupSelect' }).exists()).toBe(true);
    expect(wrapper.text()).toContain('group-a');

    await wrapper.setProps({ attributeId: [4, 5] });
    await flushPromises();
    expect(mocks.groupApi.fetchStorageRealTimeDataById).toHaveBeenCalledWith(5, expect.any(Object));
  });
});

describe('storage cluster detail error coverage', () => {
  it('shows API errors for analytics tabs, events, and export while keeping the UI usable', async () => {
    mocks.storageClusterApi.fetchCapacityChange.mockRejectedValueOnce(new Error('capacity'));
    const wrapper = await mountPage(StorageClusterDetailPage);
    expect(mocks.error).toHaveBeenCalledWith('加载容量趋势失败，请稍后重试');

    mocks.aggregateApi.fetchAggregateTrees.mockRejectedValueOnce(new Error('distribution'));
    await wrapper.findComponent({ name: 'ElTabs' }).vm.$emit('update:modelValue', 'distribution');
    await flushPromises();
    expect(mocks.error).toHaveBeenCalledWith('加载存储分布失败，请稍后重试');

    mocks.storageClusterApi.fetchTopLatency.mockRejectedValueOnce(new Error('performance'));
    await wrapper.findComponent({ name: 'ElTabs' }).vm.$emit('update:modelValue', 'performance');
    await flushPromises();
    expect(mocks.error).toHaveBeenCalledWith('加载性能数据失败，请稍后重试');

    mocks.storageClusterApi.fetchErrorSeverity.mockRejectedValueOnce(new Error('faults'));
    await wrapper.findComponent({ name: 'ElTabs' }).vm.$emit('update:modelValue', 'faults');
    await flushPromises();
    expect(mocks.error).toHaveBeenCalledWith('加载故障数据失败，请稍后重试');

    mocks.storageClusterApi.fetchSystemEvents.mockResolvedValueOnce({ data: [], total: 1, page: 1, page_size: 20 });
    await wrapper.find('.system-events').findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await flushPromises();
    mocks.storageClusterApi.fetchSystemEvents.mockRejectedValueOnce(new Error('events'));
    await wrapper.find('.system-events').findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await flushPromises();
    expect(mocks.error).toHaveBeenCalledWith('加载系统事件失败，请稍后重试');

    mocks.storageClusterApi.exportAnalytics.mockRejectedValueOnce(new Error('export'));
    await wrapper.findComponent({ name: 'ElDropdown' }).vm.$emit('command', 'all:csv');
    await flushPromises();
    expect(mocks.error).toHaveBeenCalledWith('导出失败，请稍后重试');
  });

  it('supports analytics pagination, reset, fallback filenames, and invalid route ids', async () => {
    mocks.storageClusterApi.fetchSystemEvents.mockResolvedValue({ data: [], total: 45, page: 1, page_size: 20 });
    const wrapper = await mountPage(StorageClusterDetailPage);
    await wrapper.findComponent({ name: 'ElTabs' }).vm.$emit('update:modelValue', 'faults');
    await flushPromises();
    const pagination = wrapper.findComponent({ name: 'ElPagination' });
    await pagination.vm.$emit('current-change', 2);
    await pagination.vm.$emit('size-change', 50);
    await flushPromises();
    expect(mocks.storageClusterApi.fetchSystemEvents).toHaveBeenLastCalledWith(42, expect.objectContaining({ page: 1, page_size: 50 }));

    await wrapper.findComponent({ name: 'ElTabs' }).vm.$emit('update:modelValue', 'performance');
    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await flushPromises();
    expect(wrapper.findComponent({ name: 'ElSelect' }).exists()).toBe(true);

    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    mocks.storageClusterApi.exportAnalytics.mockResolvedValueOnce({ data: 'csv-data', headers: {} });
    await wrapper.findComponent({ name: 'ElDropdown' }).vm.$emit('command', 'all:csv');
    await flushPromises();
    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();

    wrapper.unmount();
    mocks.route.params = { id: 'not-a-number' };
    const invalidWrapper = await mountPage(StorageClusterDetailPage);
    expect(mocks.storageClusterApi.fetchById).not.toHaveBeenCalledWith(NaN);
    expect(invalidWrapper.find('.storage-health-page').exists()).toBe(true);
  });
});
