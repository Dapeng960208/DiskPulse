import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { computed, defineComponent, h, inject, nextTick, provide } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

vi.mock('@/api/support/base-request', () => ({ default: {} }));
vi.mock('@/api/support/auth-request', () => ({ default: {} }));
vi.mock('vue-router', () => ({
  RouterLink: true,
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock('@/utils/authorization', () => ({ hasRole: () => true }));
vi.mock('@/stores/current-user', () => ({
  useCurrentUser: () => ({ extensionAttributes: {} }),
}));
vi.mock('@/utils/common.js', () => ({ exportReport: vi.fn() }));

const tableRowKey = Symbol('project-environment-usage-alert-row');

const FilterFormStub = defineComponent({
  name: 'FilterForm',
  emits: ['query', 'reset', 'export'],
  setup(_, { slots }) {
    return () => h('form', [slots.default?.(), slots.exportExcel?.()]);
  },
});

const DataTableStub = defineComponent({
  name: 'DataTable',
  props: { data: Array },
  setup(props, { slots }) {
    provide(tableRowKey, computed(() => props.data?.[0]));
    return () => h('div', slots.default?.());
  },
});

const ElTableColumnStub = defineComponent({
  name: 'ElTableColumn',
  setup(_, { slots }) {
    const row = inject(tableRowKey);
    return () => h('div', row?.value ? slots.default?.({ row: row.value }) : null);
  },
});

const ElFormStub = defineComponent({
  name: 'ElForm',
  props: { model: Object, rules: Object },
  setup(_, { expose, slots }) {
    expose({
      validate: vi.fn(() => Promise.resolve()),
      clearValidate: vi.fn(),
    });
    return () => h('form', slots.default?.());
  },
});

const ElFormItemStub = defineComponent({
  name: 'ElFormItem',
  setup(_, { slots }) {
    return () => h('label', slots.default?.());
  },
});

const ElButtonStub = defineComponent({
  name: 'ElButton',
  emits: ['click'],
  setup(_, { emit, slots }) {
    return () => h('button', { onClick: () => emit('click') }, slots.default?.());
  },
});

const ElDialogStub = defineComponent({
  name: 'ElDialog',
  setup(_, { slots }) {
    return () => h('div', [slots.default?.(), slots.footer?.()]);
  },
});

const ElSelectStub = defineComponent({
  name: 'ElSelect',
  props: {
    modelValue: { type: [Number, String], default: null },
  },
  emits: ['update:modelValue'],
  setup(_, { slots }) {
    return () => h('select', slots.default?.());
  },
});

function selectStub(name) {
  return defineComponent({
    name,
    props: {
      modelValue: { type: [Number, String], default: null },
      projectId: { type: Number, default: null },
      projectEnvironmentId: { type: Number, default: null },
      storageClusterId: { type: Number, default: null },
    },
    emits: ['update:modelValue', 'change'],
    setup(_, { slots }) {
      return () => h('div', slots.default?.());
    },
  });
}

const ProjectSelectStub = selectStub('ProjectSelect');
const ProjectStorageEnvironmentSelectStub = selectStub('ProjectStorageEnvironmentSelect');
const GroupSelectStub = selectStub('GroupSelect');
const StorageClusterSelectStub = selectStub('StorageClusterSelect');
const RdUserSelectStub = selectStub('RdUserSelect');

const commonStubs = {
  DataTable: DataTableStub,
  ElButton: ElButtonStub,
  ElDatePicker: true,
  ElDescriptions: true,
  ElDescriptionsItem: true,
  ElFormItem: ElFormItemStub,
  ElInput: true,
  ElLink: true,
  ElOption: true,
  ElSelect: ElSelectStub,
  ElTableColumn: ElTableColumnStub,
  ElTag: true,
  ExportDialog: true,
  FilterForm: FilterFormStub,
  GroupSelect: GroupSelectStub,
  Progress: true,
  ProjectSelect: ProjectSelectStub,
  ProjectStorageEnvironmentSelect: ProjectStorageEnvironmentSelectStub,
  RdUserSelect: RdUserSelectStub,
  RouterLink: true,
  StorageClusterSelect: StorageClusterSelectStub,
  UsageFormDialog: true,
};

async function mountUsageList(response = { content: [], total: 0 }) {
  const { default: storageUsageApi } = await import('@/api/storage-usage-api');
  const fetch = vi.spyOn(storageUsageApi, 'fetch').mockResolvedValue(response);
  vi.spyOn(storageUsageApi, 'exportStorageUsages').mockResolvedValue(new Blob());
  const { default: UsageListPage } = await import('@/pages/usage/UsageListPage.vue');
  const wrapper = shallowMount(UsageListPage, {
    global: { stubs: commonStubs },
  });
  await flushPromises();
  return { fetch, storageUsageApi, wrapper };
}

describe('project environment usage and alert frontend contract', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
  });

  it('scopes usage filters and export to project, environment, group, cluster, and user', async () => {
    const { ElMessageBox } = await import('element-plus');
    const confirm = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue();
    const { storageUsageApi, wrapper } = await mountUsageList({
      content: [{
        id: 1,
        linux_path: '/project/env/group/alice',
        user: { rd_username: 'alice', user_type: 2 },
        project: { id: 42, name: 'Alpha' },
        project_environment: { id: 7, name: '生产环境' },
        group: { id: 31, name: '研发组' },
        storage_cluster: { id: 9, name: 'netapp-a', storage_type: 'netapp' },
        storage_target: { type: 'volume', id: 3, name: 'vol-a' },
      }],
      total: 1,
    });
    const project = wrapper.findComponent({ name: 'ProjectSelect' });
    expect(project.exists()).toBe(true);
    project.vm.$emit('update:modelValue', 42);
    await nextTick();

    const environment = wrapper.findComponent({ name: 'ProjectStorageEnvironmentSelect' });
    expect(environment.props('projectId')).toBe(42);
    environment.vm.$emit('update:modelValue', 7);
    wrapper.findComponent({ name: 'GroupSelect' }).vm.$emit('update:modelValue', 31);
    wrapper.findComponent({ name: 'StorageClusterSelect' }).vm.$emit('update:modelValue', 9);
    wrapper.findComponent({ name: 'RdUserSelect' }).vm.$emit('update:modelValue', 5);
    await nextTick();

    expect(wrapper.findComponent({ name: 'GroupSelect' }).props('projectEnvironmentId')).toBe(7);
    wrapper.findComponent(FilterFormStub).vm.$emit('query');
    await flushPromises();
    expect(storageUsageApi.fetch).toHaveBeenLastCalledWith(expect.objectContaining({
      project_id: 42,
      project_environment_id: 7,
      group_id: 31,
      storage_cluster_id: 9,
      user_id: 5,
    }));

    wrapper.findComponent(FilterFormStub).vm.$emit('export');
    await nextTick();
    wrapper.findComponent({ name: 'ExportDialog' }).vm.$emit('submitted', 'excel');
    expect(storageUsageApi.exportStorageUsages).toHaveBeenCalledWith(expect.objectContaining({
      export_type: 'excel',
      project_id: 42,
      project_environment_id: 7,
      group_id: 31,
      storage_cluster_id: 9,
      user_id: 5,
    }));

    await wrapper.findAll('button').find((button) => button.text() === '移至备份').trigger('click');
    expect(confirm).toHaveBeenCalled();
  });

  it('derives the create payload from an environment-scoped group without cluster override', async () => {
    const { default: groupApi } = await import('@/api/group-api');
    vi.spyOn(groupApi, 'fetchById').mockResolvedValue({
      id: 31,
      linux_path: '/project/env/group',
      project_environment: { id: 7, name: '生产环境' },
      storage_cluster: { id: 9, name: 'netapp-a', storage_type: 'netapp' },
    });
    const { default: userApi } = await import('@/api/users-api');
    vi.spyOn(userApi, 'fetchById').mockResolvedValue({ id: 5, rd_username: 'alice' });
    const { default: storageUsageApi } = await import('@/api/storage-usage-api');
    const create = vi.spyOn(storageUsageApi, 'create').mockResolvedValue({ id: 1 });
    const { default: UsageFormDialog } = await import(
      '@/pages/usage/components/UsageFormDialog.vue'
    );
    const wrapper = shallowMount(UsageFormDialog, {
      global: {
        stubs: {
          ElButton: ElButtonStub,
          ElDialog: ElDialogStub,
          ElForm: ElFormStub,
          ElFormItem: ElFormItemStub,
          ElInput: true,
          GroupSelect: GroupSelectStub,
          ProjectSelect: ProjectSelectStub,
          ProjectStorageEnvironmentSelect: ProjectStorageEnvironmentSelectStub,
          RdUserSelect: RdUserSelectStub,
          StorageClusterSelect: StorageClusterSelectStub,
        },
      },
    });
    wrapper.vm.$.exposed.edit();
    await nextTick();
    const form = wrapper.findComponent(ElFormStub);

    const project = wrapper.findComponent({ name: 'ProjectSelect' });
    expect(project.exists()).toBe(true);
    project.vm.$emit('update:modelValue', 42);
    await nextTick();
    wrapper.findComponent({ name: 'ProjectStorageEnvironmentSelect' }).vm.$emit('update:modelValue', 7);
    await nextTick();
    expect(wrapper.findComponent({ name: 'GroupSelect' }).props('projectEnvironmentId')).toBe(7);

    Object.assign(form.props('model'), {
      group_id: 31,
      user_id: 5,
      storage_cluster_id: 999,
    });
    wrapper.findComponent({ name: 'GroupSelect' }).vm.$emit('change', 31);
    await flushPromises();
    expect(wrapper.text()).toContain('netapp-a');
    expect(wrapper.findComponent({ name: 'StorageClusterSelect' }).exists()).toBe(false);

    const submit = wrapper.findAll('button').find((button) => button.text() === '提交');
    await submit.trigger('click');
    await flushPromises();
    expect(create).toHaveBeenCalledWith({ group_id: 31, user_id: 5 });
  });

  it('renders the frozen usage export context from minimal references', async () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/pages/usage/UsageListPage.vue'),
      'utf8',
    );
    for (const label of [
      '项目',
      '项目环境',
      '存储集群',
      '存储类型',
      '项目组',
      'Volume',
      'Qtree',
      'Linux路径',
    ]) {
      expect(source).toContain(`label="${label}"`);
    }
    expect(source).toContain('project_environment?.name');
    expect(source).toContain('row.project?.name');
    expect(source).not.toContain('row.group?.project?.name');
    expect(source).toContain('storage_cluster?.storage_type');
    expect(source).toContain('storage_target?.type');
    expect(source).toContain('storage_target?.name');
  });

  it('sends the exact environment alert filter and shows group project context', async () => {
    const { default: alertApi } = await import('@/api/alert-api');
    vi.spyOn(alertApi, 'fetch').mockResolvedValue({
      content: [{
        id: 1,
        related_type: 'Group',
        description: 'Group usage high',
        alert_type: 'alert',
        alert_level: 'high',
        related_info: {
          project: { id: 42, name: 'Alpha' },
          project_environment: { id: 7, name: '生产环境' },
          group: { id: 31, name: '研发组' },
        },
      }],
      total: 1,
    });
    const { default: AlertListPage } = await import('@/pages/alert/AlertListPage.vue');
    const wrapper = shallowMount(AlertListPage, {
      global: { stubs: commonStubs },
    });
    await flushPromises();

    const project = wrapper.findComponent({ name: 'ProjectSelect' });
    expect(project.exists()).toBe(true);
    project.vm.$emit('update:modelValue', 42);
    await nextTick();
    const environment = wrapper.findComponent({ name: 'ProjectStorageEnvironmentSelect' });
    expect(environment.props('projectId')).toBe(42);
    environment.vm.$emit('update:modelValue', 7);
    wrapper.findComponent(FilterFormStub).vm.$emit('query');
    await flushPromises();

    expect(alertApi.fetch).toHaveBeenLastCalledWith(expect.objectContaining({
      related_type: 'ProjectStorageEnvironment',
      related_id: 7,
    }));
    expect(alertApi.fetch.mock.calls.at(-1)[0]).not.toHaveProperty('project_environment_id');
    expect(wrapper.text()).toContain('Alpha');
    expect(wrapper.text()).toContain('生产环境');

    const alertSelects = wrapper.findAllComponents(ElSelectStub);
    alertSelects[0].vm.$emit('update:modelValue', 'report');
    alertSelects[1].vm.$emit('update:modelValue', 'Group');
    wrapper.findComponent(FilterFormStub).vm.$emit('reset');
    await flushPromises();
    expect(alertApi.fetch).toHaveBeenLastCalledWith(expect.objectContaining({
      alert_type: '',
    }));
  });
});
