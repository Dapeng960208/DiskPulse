import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  backupApi: { fetch: vi.fn(), deleteById: vi.fn(), rollBackedBackUpStorageById: vi.fn() },
  configApi: { fetch: vi.fn(), updateConfig: vi.fn() },
  aiApi: {
    listAdminModels: vi.fn(), listAudits: vi.fn(), createModel: vi.fn(), updateModel: vi.fn(),
    testModel: vi.fn(), deleteModel: vi.fn(),
  },
  aggregateApi: { fetch: vi.fn(), fetchAggregateTrees: vi.fn() },
  qtreeApi: { fetch: vi.fn() },
  volumeApi: { fetch: vi.fn() },
  storageClusterApi: {
    fetch: vi.fn(), fetchById: vi.fn(), fetchCapacityChange: vi.fn(), fetchTopLatency: vi.fn(),
    fetchErrorSeverity: vi.fn(), fetchRepeatedFaults: vi.fn(), fetchSystemEvents: vi.fn(),
    exportAnalytics: vi.fn(),
  },
  usersApi: { fetch: vi.fn(), deleteById: vi.fn(), syncLdap: vi.fn(), fetchProfile: vi.fn() },
  route: { query: {}, params: { id: '42' } },
  router: { push: vi.fn(), replace: vi.fn() },
  confirm: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  hasRole: vi.fn(),
  hasAnyRole: vi.fn(),
  currentUser: { id: 1, extensionAttributes: { rdUsername: null }, setCurrentUser: vi.fn() },
  createRouter: vi.fn(),
  createWebHistory: vi.fn(),
  beforeEachHook: vi.fn(),
  afterEachHook: vi.fn(),
  updatePageSubtitle: vi.fn(),
  processRoutes: vi.fn(),
  shouldUpdatePageSubtitle: vi.fn(),
  formDialogEdit: vi.fn(),
}));

vi.mock('@/api/storage-back-up-record-api.js', () => ({ default: mocks.backupApi }));
vi.mock('@/api/config-api', () => ({ default: mocks.configApi }));
vi.mock('@/api/ai-api', () => ({ default: mocks.aiApi }));
vi.mock('@/api/aggregate-api.js', () => ({ default: mocks.aggregateApi }));
vi.mock('@/api/qtree-api.js', () => ({ default: mocks.qtreeApi }));
vi.mock('@/api/volume-api.js', () => ({ default: mocks.volumeApi }));
vi.mock('@/api/storage-cluster-api', () => ({ default: mocks.storageClusterApi }));
vi.mock('@/api/users-api', () => ({ default: mocks.usersApi }));
vi.mock('@/utils/authorization', () => ({ hasRole: mocks.hasRole, hasAnyRole: mocks.hasAnyRole }));
vi.mock('@/stores/current-user', () => ({ useCurrentUser: () => mocks.currentUser }));
vi.mock('@/composables/common', () => ({ getDefaultTime: () => ['2026-07-01 00:00:00', '2026-07-02 00:00:00'] }));
vi.mock('@/router/routes', () => ({ default: [{ path: '/', meta: {}, children: [] }] }));
vi.mock('@/router/support/accessibility', () => ({
  processRoutes: mocks.processRoutes,
  shouldUpdatePageSubtitle: mocks.shouldUpdatePageSubtitle,
}));
vi.mock('@/utils', () => ({ updatePageSubtitle: mocks.updatePageSubtitle }));
vi.mock('nprogress', () => ({ default: { configure: vi.fn(), start: vi.fn(), done: vi.fn() } }));
vi.mock('vue-router', async () => ({
  ...(await vi.importActual('vue-router')),
  useRoute: () => mocks.route,
  useRouter: () => mocks.router,
  createRouter: (...args) => mocks.createRouter(...args),
  createWebHistory: (...args) => mocks.createWebHistory(...args),
}));
vi.mock('element-plus', async () => ({
  ...(await vi.importActual('element-plus')),
  ElMessageBox: { confirm: mocks.confirm },
  ElMessage: { success: mocks.success, error: mocks.error, warning: mocks.warning },
}));

const passthrough = (name, tag = 'div') => defineComponent({
  name,
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    return () => h(tag, attrs, [
      ...(slots.default?.() || []),
      ...(slots.header?.() || []),
      ...(slots.footer?.() || []),
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
  props: { modelValue: { type: [String, Number, Array], default: '' }, placeholder: String },
  emits: ['update:modelValue', 'change'],
  setup(props, { emit, slots }) {
    return () => h('select', {
      value: props.modelValue,
      onChange: (event) => {
        emit('update:modelValue', event.target.value);
        emit('change', event.target.value);
      },
    }, slots.default?.());
  },
});

const namedSelect = (name) => defineComponent({
  name,
  props: { modelValue: { type: [String, Number, Array], default: '' }, placeholder: String },
  emits: ['update:modelValue', 'change'],
  setup(props, { emit, slots }) {
    return () => h('select', {
      value: props.modelValue,
      onChange: (event) => {
        emit('update:modelValue', event.target.value);
        emit('change', event.target.value);
      },
    }, slots.default?.());
  },
});

const TableColumn = defineComponent({
  name: 'ElTableColumn',
  props: { label: String },
  setup(props, { slots }) {
    return () => h('div', { 'data-column': props.label || '' }, [
      ...(slots.header?.() || []),
      ...(slots.default?.({ row: globalThis.__adminCoverageRow }) || []),
    ]);
  },
});

const Table = defineComponent({
  name: 'ElTable',
  props: { data: { type: Array, default: () => [] } },
  emits: ['row-click'],
  setup(props, { attrs, slots }) {
    return () => h('div', { ...attrs, 'data-table-data': JSON.stringify(props.data) }, slots.default?.());
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

const FilterForm = defineComponent({
  name: 'FilterForm',
  emits: ['query', 'reset', 'export'],
  setup(_, { slots }) {
    return () => h('form', { 'data-testid': 'filter-form' }, [
      ...(slots.default?.() || []),
      ...(slots.actions?.() || []),
    ]);
  },
});

const Tabs = defineComponent({
  name: 'ElTabs',
  props: { modelValue: String },
  emits: ['update:modelValue'],
  setup(_, { slots }) {
    return () => h('div', { 'data-testid': 'tabs' }, slots.default?.());
  },
});

const Dialog = defineComponent({
  name: 'ElDialog',
  props: { modelValue: Boolean },
  emits: ['update:modelValue'],
  setup(props, { slots }) {
    return () => props.modelValue ? h('div', { 'data-testid': 'dialog' }, [
      ...(slots.header?.() || []),
      ...(slots.default?.() || []),
      ...(slots.footer?.() || []),
    ]) : null;
  },
});

const Dropdown = defineComponent({
  name: 'ElDropdown',
  setup(_, { attrs, slots }) {
    return () => h('div', attrs, [
      ...(slots.default?.() || []),
      ...(slots.dropdown?.() || []),
    ]);
  },
});
const DropdownItem = defineComponent({
  name: 'ElDropdownItem',
  props: { command: String, disabled: Boolean },
  emits: ['click'],
  setup(props, { emit, slots }) {
    return () => h('button', {
      disabled: props.disabled,
      onClick: () => emit('click'),
    }, slots.default?.());
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

const Tag = defineComponent({
  name: 'ElTag',
  props: { closable: Boolean, type: String },
  setup(props, { slots }) {
    return () => h('span', { 'data-tag-type': props.type }, slots.default?.());
  },
});

const FormStub = passthrough('StorageAlertRuleForm');
const UserFormDialog = defineComponent({
  name: 'UserFormDialog',
  setup(_, { expose }) {
    expose({ edit: mocks.formDialogEdit });
    return () => h('div');
  },
});

const stubs = {
  FilterForm,
  DataTable,
  ElButton: Button,
  ElCard: passthrough('ElCard'),
  ElDatePicker: passthrough('ElDatePicker', 'input'),
  ElDescriptions: passthrough('ElDescriptions'),
  ElDescriptionsItem: passthrough('ElDescriptionsItem'),
  ElDialog: Dialog,
  ElDropdown: Dropdown,
  ElDropdownItem: DropdownItem,
  ElDropdownMenu: passthrough('ElDropdownMenu'),
  ElForm: passthrough('ElForm', 'form'),
  ElFormItem: passthrough('ElFormItem'),
  ElInput: Input,
  ElInputNumber: Input,
  ElOption: passthrough('ElOption', 'option'),
  ElPagination: Pagination,
  ElSelect: Select,
  ElSwitch: defineComponent({ name: 'ElSwitch', props: { modelValue: Boolean }, template: '<input type="checkbox" />' }),
  ElTable: Table,
  ElTableColumn: TableColumn,
  ElTabs: Tabs,
  ElTabPane: passthrough('ElTabPane'),
  ElTag: Tag,
  StorageAlertRuleForm: FormStub,
  UserFormDialog,
  RouterLink: passthrough('RouterLink', 'a'),
  RdUserSelect: namedSelect('RdUserSelect'),
  StorageClusterSelect: namedSelect('StorageClusterSelect'),
  VolumeSelect: namedSelect('VolumeSelect'),
  Progress: passthrough('Progress'),
  LoadingCharts: passthrough('LoadingCharts'),
  DiskUsage: passthrough('DiskUsage'),
  LineCharts: passthrough('LineCharts'),
  PieCharts: passthrough('PieCharts'),
  BarStackChart: passthrough('BarStackChart'),
};

const mounted = [];
const mountPage = async (component) => {
  const wrapper = shallowMount(component, {
    global: {
      plugins: [createPinia()],
      stubs,
      directives: { loading: () => undefined },
    },
  });
  mounted.push(wrapper);
  await flushPromises();
  return wrapper;
};

const button = (wrapper, text) => wrapper.findAll('button').find((item) => item.text().includes(text));

const backupRow = {
  id: 7,
  destination_path: '/backup/to',
  source_path: '/data/from',
  status: 2,
  user: { rd_username: 'alice', user_type: 2 },
};
const resourceRow = {
  id: 8,
  name: 'volume-a',
  limit: 0,
  soft_limit: 0,
  used: 2048,
  storage_cluster: { name: 'cluster-a' },
  volume: { name: 'volume-a' },
};

const rule = {
  quota_basis: 'hard',
  important: { threshold: 70, repeat_hours: 4 },
  serious: { threshold: 80, repeat_hours: 8 },
  emergency: { threshold: 90, repeat_hours: 12 },
};

beforeEach(() => {
  globalThis.__adminCoverageRow = backupRow;
  HTMLAnchorElement.prototype.click = vi.fn();
  mocks.route.query = {};
  mocks.route.params = { id: '42' };
  mocks.currentUser.id = 1;
  mocks.hasRole.mockReturnValue(true);
  mocks.hasAnyRole.mockReturnValue(true);
  mocks.confirm.mockResolvedValue(undefined);
  mocks.backupApi.fetch.mockResolvedValue({ content: [backupRow], total: 1 });
  mocks.backupApi.deleteById.mockResolvedValue({});
  mocks.backupApi.rollBackedBackUpStorageById.mockResolvedValue({});
  mocks.configApi.fetch.mockResolvedValue({ storage_alert_rule: rule });
  mocks.configApi.updateConfig.mockResolvedValue({ storage_alert_rule: rule });
  mocks.aiApi.listAdminModels.mockResolvedValue([{ id: 2, name: 'GPT', provider: 'openai', model: 'gpt', enabled: true, enable_chat: true }]);
  mocks.aiApi.listAudits.mockResolvedValue({ content: [{ id: 5, status: 'failed' }], total: 1 });
  mocks.aiApi.createModel.mockResolvedValue({});
  mocks.aiApi.updateModel.mockResolvedValue({});
  mocks.aiApi.testModel.mockResolvedValue({ message: '连接成功', reply: 'OK' });
  mocks.aiApi.deleteModel.mockResolvedValue({});
  mocks.aggregateApi.fetch.mockResolvedValue({ content: [resourceRow], total: 1 });
  mocks.aggregateApi.fetchAggregateTrees.mockResolvedValue({ data: [] });
  mocks.qtreeApi.fetch.mockResolvedValue({ content: [resourceRow], total: 1 });
  mocks.volumeApi.fetch.mockResolvedValue({ content: [resourceRow], total: 1 });
  mocks.storageClusterApi.fetchById.mockResolvedValue({ id: 42, name: 'cluster-a', storage_type: 'netapp' });
  mocks.storageClusterApi.fetchCapacityChange.mockResolvedValue({ data: [] });
  mocks.storageClusterApi.fetchTopLatency.mockResolvedValue({ supported: true, data: [] });
  mocks.storageClusterApi.fetchErrorSeverity.mockResolvedValue({ total: 1, counts: { error: 1 } });
  mocks.storageClusterApi.fetchRepeatedFaults.mockResolvedValue({ data: [{ source: 'netapp', fingerprint: 'f1' }] });
  mocks.storageClusterApi.fetchSystemEvents.mockResolvedValue({ data: [{ event_code: 'E1' }], total: 1, page: 1, page_size: 20 });
  mocks.storageClusterApi.exportAnalytics.mockResolvedValue({ data: new Blob(['report']), headers: {} });
  mocks.usersApi.fetch.mockResolvedValue({ content: [resourceRow], total: 1 });
  mocks.usersApi.deleteById.mockResolvedValue({});
  mocks.usersApi.syncLdap.mockResolvedValue({ ldap_total: 1, created: 1, updated: 0, reactivated: 0, marked_inactive: 0 });
  mocks.usersApi.fetchProfile.mockResolvedValue({ result: { id: 1 } });
  mocks.success.mockReset();
  mocks.error.mockReset();
  mocks.warning.mockReset();
});

afterEach(() => {
  mounted.splice(0).forEach((wrapper) => wrapper.unmount());
});

describe('admin list coverage', () => {
  it('covers backup filters, pagination, delete, rollback and permission branches', async () => {
    const { default: Page } = await import('@/pages/admin/backup/BackUpListPage.vue');
    const wrapper = await mountPage(Page);
    expect(mocks.backupApi.fetch).toHaveBeenCalled();

    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await wrapper.findComponent({ name: 'DataTable' }).vm.$emit('update:pagination', {
      page: 2, pageSize: 50, prop: 'id', order: 'descending',
    });
    await flushPromises();
    expect(mocks.backupApi.fetch).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2, size: 50, prop: 'id' }));

    await button(wrapper, '删除备份').trigger('click');
    const deleteOptions = mocks.confirm.mock.calls.at(-1)[2];
    const cancelled = vi.fn();
    await deleteOptions.beforeClose('cancel', {}, cancelled);
    expect(cancelled).toHaveBeenCalled();
    const done = vi.fn();
    await deleteOptions.beforeClose('confirm', { confirmButtonLoading: false }, done);
    await flushPromises();
    expect(mocks.backupApi.deleteById).toHaveBeenCalledWith(7);
    expect(mocks.success).toHaveBeenCalledWith('备份删除成功');

    await button(wrapper, '回滚备份').trigger('click');
    const rollbackOptions = mocks.confirm.mock.calls.at(-1)[2];
    await rollbackOptions.beforeClose('confirm', { confirmButtonLoading: false }, vi.fn());
    await flushPromises();
    expect(mocks.backupApi.rollBackedBackUpStorageById).toHaveBeenCalledWith(7);

    mocks.hasRole.mockReturnValue(false);
    const restricted = await mountPage(Page);
    expect(button(restricted, '删除备份')).toBeUndefined();
    expect(button(restricted, '回滚备份')).toBeUndefined();
  });

  it('covers aggregate, volume and qtree filters, warnings and route actions', async () => {
    globalThis.__adminCoverageRow = resourceRow;
    const { default: Aggregate } = await import('@/pages/admin/aggregate/AggregateListPage.vue');
    const { default: Volume } = await import('@/pages/admin/volume/VolumeListPage.vue');
    const { default: Qtree } = await import('@/pages/admin/qtree/QtreeListPage.vue');

    const aggregate = await mountPage(Aggregate);
    await aggregate.findComponent({ name: 'FilterForm' }).vm.$emit('query');
    await aggregate.findComponent({ name: 'DataTable' }).vm.$emit('update:pagination', { page: 3, pageSize: 50 });
    await flushPromises();
    await button(aggregate, '详情').trigger('click');
    expect(mocks.router.push).toHaveBeenCalledWith({ path: '/admin/aggregate/8' });

    globalThis.__adminCoverageRow = { ...resourceRow, limit: 1024, soft_limit: 2048, used: 2048 };
    const volume = await mountPage(Volume);
    await volume.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await volume.findComponent({ name: 'DataTable' }).vm.$emit('update:pagination', { page: 2, pageSize: 100 });
    await flushPromises();
    await button(volume, '详情').trigger('click');
    expect(mocks.router.push).toHaveBeenCalledWith({ path: '/admin/volume/8' });

    const qtree = await mountPage(Qtree);
    const cluster = qtree.findComponent({ name: 'StorageClusterSelect' });
    mocks.storageClusterApi.fetchById.mockResolvedValueOnce({ id: 9, storage_type: 'isilon' });
    await cluster.vm.$emit('update:modelValue', 9);
    await flushPromises();
    expect(mocks.warning).toHaveBeenCalledWith('Isilon 不支持 Qtree');
    await qtree.findComponent({ name: 'FilterForm' }).vm.$emit('query');
    mocks.storageClusterApi.fetchById.mockResolvedValueOnce({ id: 10, storage_type: 'netapp' });
    await cluster.vm.$emit('update:modelValue', 10);
    await flushPromises();
    await qtree.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await qtree.findComponent({ name: 'DataTable' }).vm.$emit('update:pagination', { page: 4, pageSize: 20 });
    await flushPromises();
    await button(qtree, '详情').trigger('click');
    expect(mocks.router.push).toHaveBeenCalledWith({ path: '/admin/qtree/8' });
  });

  it('keeps resource detail actions hidden when the admin role is absent', async () => {
    mocks.hasRole.mockReturnValue(false);
    globalThis.__adminCoverageRow = resourceRow;
    const { default: Aggregate } = await import('@/pages/admin/aggregate/AggregateListPage.vue');
    const { default: Volume } = await import('@/pages/admin/volume/VolumeListPage.vue');
    const { default: Qtree } = await import('@/pages/admin/qtree/QtreeListPage.vue');
    expect(button(await mountPage(Aggregate), '详情')).toBeUndefined();
    expect(button(await mountPage(Volume), '详情')).toBeUndefined();
    expect(button(await mountPage(Qtree), '详情')).toBeUndefined();
  });
});

describe('admin settings, AI and users coverage', () => {
  it('covers settings validity, save and busy guard through the page UI', async () => {
    const { default: Page } = await import('@/pages/admin/settings/SettingsPage.vue');
    const wrapper = await mountPage(Page);
    const ruleForm = wrapper.findComponent({ name: 'StorageAlertRuleForm' });
    await ruleForm.vm.$emit('validity-change', false);
    expect(wrapper.find('button').attributes('disabled')).toBeDefined();
    await ruleForm.vm.$emit('validity-change', true);
    await wrapper.find('button').trigger('click');
    await flushPromises();
    expect(mocks.configApi.updateConfig).toHaveBeenCalledWith(expect.objectContaining({ storage_alert_rule: rule }));
    expect(mocks.success).toHaveBeenCalledWith('系统设置已保存');

    let release;
    mocks.configApi.updateConfig.mockClear();
    mocks.configApi.updateConfig.mockImplementationOnce(() => new Promise((resolve) => { release = resolve; }));
    const busy = await mountPage(Page);
    await busy.find('button').trigger('click');
    await busy.find('button').trigger('click');
    expect(mocks.configApi.updateConfig).toHaveBeenCalledTimes(1);
    release({ storage_alert_rule: rule });
    await flushPromises();
  });

  it('covers AI model create, edit, test, delete, audit tab and row routing', async () => {
    globalThis.__adminCoverageRow = { id: 2, name: 'GPT', provider: 'openai', model: 'gpt', enabled: true, enable_chat: true, status: 'failed' };
    const { default: Page } = await import('@/pages/admin/ai/AiCenterPage.vue');
    const wrapper = await mountPage(Page);

    await button(wrapper, '新增模型').trigger('click');
    const inputs = wrapper.findAllComponents({ name: 'ElInput' });
    await inputs[0].vm.$emit('update:modelValue', '新模型');
    await inputs[3].vm.$emit('update:modelValue', 'gpt-test');
    await button(wrapper, '创建模型').trigger('click');
    await flushPromises();
    expect(mocks.aiApi.createModel).toHaveBeenCalledWith(expect.objectContaining({ name: '新模型', model: 'gpt-test' }));

    await button(wrapper, '编辑').trigger('click');
    await button(wrapper, '保存修改').trigger('click');
    await flushPromises();
    expect(mocks.aiApi.updateModel).toHaveBeenCalledWith(2, expect.not.objectContaining({ api_key: expect.anything() }));

    await button(wrapper, '连接测试').trigger('click');
    expect(mocks.aiApi.testModel).toHaveBeenCalledWith(2);
    await button(wrapper, '删除').trigger('click');
    await flushPromises();
    expect(mocks.aiApi.deleteModel).toHaveBeenCalledWith(2);

    await wrapper.findComponent({ name: 'ElTabs' }).vm.$emit('update:modelValue', 'audit');
    await flushPromises();
    expect(mocks.aiApi.listAudits).toHaveBeenCalledWith(expect.objectContaining({ status: undefined }));
    const auditTable = wrapper.findAllComponents({ name: 'ElTable' }).at(-1);
    await auditTable.vm.$emit('row-click', { id: 5 });
    expect(mocks.router.push).toHaveBeenCalledWith('/admin/ai-center/audits/5');
    await button(wrapper, '刷新').trigger('click');
    await flushPromises();
  });

  it('covers user query-from-route, delete confirmation and cancelled LDAP sync', async () => {
    globalThis.__adminCoverageRow = { id: 3, rd_username: 'alice', username: 'Alice', user_type: 2, is_alert: true, storage_used: 4 };
    mocks.route.query = { nameLike: 'alice' };
    const { default: Page } = await import('@/pages/admin/user/UserListPage.vue');
    const wrapper = await mountPage(Page);
    expect(mocks.usersApi.fetch).toHaveBeenCalledWith(expect.objectContaining({ nameLike: 'alice' }));

    await wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await wrapper.findComponent({ name: 'DataTable' }).vm.$emit('update:pagination', { page: 2, pageSize: 50 });
    await button(wrapper, '删除').trigger('click');
    const options = mocks.confirm.mock.calls.at(-1)[2];
    const done = vi.fn();
    await options.beforeClose('cancel', {}, done);
    await options.beforeClose('confirm', { confirmButtonLoading: false }, done);
    await flushPromises();
    expect(mocks.usersApi.deleteById).toHaveBeenCalledWith(3);

    await button(wrapper, '新增用户').trigger('click');
    expect(mocks.formDialogEdit).toHaveBeenCalledWith();
    mocks.confirm.mockRejectedValueOnce(new Error('cancelled'));
    await button(wrapper, '同步LDAP').trigger('click');
    await flushPromises();
    expect(mocks.usersApi.syncLdap).not.toHaveBeenCalled();
  });
});

describe('storage cluster detail coverage', () => {
  it('covers tabs, filters, pagination, export and successful loaders', async () => {
    const { default: Page } = await import('@/pages/admin/storage-cluster/StorageClusterDetailPage.vue');
    const wrapper = await mountPage(Page);
    const tabs = wrapper.findComponent({ name: 'ElTabs' });
    expect(mocks.storageClusterApi.fetchCapacityChange).toHaveBeenCalledWith(42, expect.any(Object));

    await tabs.vm.$emit('update:modelValue', 'distribution');
    await flushPromises();
    expect(mocks.aggregateApi.fetchAggregateTrees).toHaveBeenCalledWith({ storage_cluster_id: 42 });

    mocks.storageClusterApi.fetchTopLatency.mockResolvedValueOnce({ supported: false, data: [] });
    await tabs.vm.$emit('update:modelValue', 'performance');
    await flushPromises();
    const performanceFilter = wrapper.findAllComponents({ name: 'FilterForm' }).at(0);
    await performanceFilter.vm.$emit('reset');
    await flushPromises();

    await tabs.vm.$emit('update:modelValue', 'faults');
    await flushPromises();
    const filters = wrapper.findAllComponents({ name: 'FilterForm' });
    const eventFilter = filters.at(-1);
    const keyword = wrapper.findAllComponents({ name: 'ElInput' })
      .find((item) => item.props('placeholder') === '事件代码、对象或内容');
    const severity = wrapper.findAllComponents({ name: 'ElSelect' })
      .find((item) => item.props('placeholder') === '全部等级');
    await keyword.vm.$emit('update:modelValue', ' E1 ');
    await severity.vm.$emit('update:modelValue', 'error');
    await eventFilter.vm.$emit('query');
    await flushPromises();
    expect(mocks.storageClusterApi.fetchSystemEvents).toHaveBeenLastCalledWith(42, expect.objectContaining({ keyword: 'E1', severity: 'error' }));

    const pagination = wrapper.findComponent({ name: 'ElPagination' });
    await pagination.vm.$emit('current-change', 2);
    await pagination.vm.$emit('size-change', 50);
    await flushPromises();
    await eventFilter.vm.$emit('reset');
    await flushPromises();

    await wrapper.findComponent({ name: 'ElDropdown' }).vm.$emit('command', 'all:csv');
    await flushPromises();
    expect(mocks.storageClusterApi.exportAnalytics).toHaveBeenCalledWith(42, expect.objectContaining({ section: 'all', format: 'csv' }));
  });

  it('covers detail loader and export error branches', async () => {
    mocks.storageClusterApi.fetchCapacityChange.mockRejectedValueOnce(new Error('capacity'));
    const { default: Page } = await import('@/pages/admin/storage-cluster/StorageClusterDetailPage.vue');
    const wrapper = await mountPage(Page);
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

    mocks.storageClusterApi.fetchSystemEvents.mockRejectedValueOnce(new Error('events'));
    await wrapper.findAllComponents({ name: 'FilterForm' }).at(-1).vm.$emit('query');
    await flushPromises();
    expect(mocks.error).toHaveBeenCalledWith('加载系统事件失败，请稍后重试');

    mocks.storageClusterApi.exportAnalytics.mockRejectedValueOnce(new Error('export'));
    await wrapper.findComponent({ name: 'ElDropdown' }).vm.$emit('command', 'all:excel');
    await flushPromises();
    expect(mocks.error).toHaveBeenCalledWith('导出失败，请稍后重试');
  });
});

describe('router guard coverage', () => {
  it('covers public, profile, accessibility and failure guard paths', async () => {
    let guard;
    mocks.beforeEachHook.mockImplementation((handler) => { guard = handler; });
    mocks.createRouter.mockImplementation((options) => ({
      ...options,
      beforeEach: mocks.beforeEachHook,
      afterEach: mocks.afterEachHook,
    }));
    mocks.createWebHistory.mockReturnValue('history');
    const { default: router } = await import('@/router/index');
    expect(router).toBeTruthy();

    await guard({ path: '/login', meta: {} }, { path: '/', meta: {} });
    mocks.currentUser.id = null;
    await guard({ path: '/secure', meta: { isAccessible: () => 200 } }, { path: '/', meta: {} });
    expect(mocks.usersApi.fetchProfile).toHaveBeenCalled();
    mocks.currentUser.id = 1;
    await guard({ path: '/secure', meta: { isAccessible: () => 403 } }, {});
    await guard({ path: '/secure', meta: { isAccessible: () => 404 } }, {});
    await guard({ path: '/secure', meta: { isAccessible: () => 401 } }, {});
    await guard({ path: '/secure', meta: {} }, {});
    await guard({ path: '/secure', meta: { isPublic: true } }, {});
    mocks.usersApi.fetchProfile.mockRejectedValueOnce(new Error('profile'));
    mocks.currentUser.id = null;
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    await guard({ path: '/secure', meta: {} }, {});
    errorSpy.mockRestore();
  });
});
