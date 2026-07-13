import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import {
  computed,
  defineComponent,
  h,
  inject,
  nextTick,
  provide,
} from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

const route = { params: { id: '42' } };

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('@/utils/authorization', () => ({
  hasRole: () => true,
}));

const tableRowKey = Symbol('project-storage-environment-row');

const DataTableStub = defineComponent({
  name: 'DataTable',
  props: {
    data: Array,
    loading: Boolean,
    pagination: Object,
  },
  emits: ['update:pagination'],
  setup(props, { slots }) {
    provide(tableRowKey, computed(() => props.data?.[0]));
    return () => h('div', slots.default?.());
  },
});

const ElTableColumnStub = defineComponent({
  name: 'ElTableColumn',
  setup(_, { slots }) {
    const row = inject(tableRowKey);
    return () => h('div', [
      slots.header?.(),
      row?.value ? slots.default?.({ row: row.value }) : null,
    ]);
  },
});

const ElButtonStub = defineComponent({
  name: 'ElButton',
  emits: ['click'],
  setup(_, { emit, slots }) {
    return () => h('button', { onClick: () => emit('click') }, slots.default?.());
  },
});

const ElEmptyStub = defineComponent({
  name: 'ElEmpty',
  props: { description: String },
  setup(props) {
    return () => h('div', props.description);
  },
});

const ElAlertStub = defineComponent({
  name: 'ElAlert',
  props: { title: String },
  setup(props) {
    return () => h('div', props.title);
  },
});

const ElFormStub = defineComponent({
  name: 'ElForm',
  props: {
    model: Object,
    rules: Object,
  },
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
  props: {
    label: String,
    prop: String,
  },
  setup(props, { slots }) {
    return () => h('label', [props.label, slots.default?.()]);
  },
});

const ElDialogStub = defineComponent({
  name: 'ElDialog',
  setup(_, { slots }) {
    return () => h('div', [slots.default?.(), slots.footer?.()]);
  },
});

const tableStubs = {
  DataTable: DataTableStub,
  ProjectStorageEnvironmentFormDialog: true,
  ElAlert: ElAlertStub,
  ElButton: ElButtonStub,
  ElEmpty: ElEmptyStub,
  ElTableColumn: ElTableColumnStub,
  ElTag: true,
};

async function mountEnvironmentTable(response) {
  const { default: environmentApi } = await import('@/api/project-storage-environment-api');
  const fetchByProject = vi.spyOn(environmentApi, 'fetchByProject');
  if (response instanceof Error) {
    fetchByProject.mockRejectedValue(response);
  } else {
    fetchByProject.mockResolvedValue(response);
  }
  const { default: ProjectStorageEnvironmentTable } = await import(
    '@/pages/project/components/ProjectStorageEnvironmentTable.vue'
  );
  const wrapper = shallowMount(ProjectStorageEnvironmentTable, {
    props: { projectId: 42 },
    global: { stubs: tableStubs },
  });
  await flushPromises();
  return { environmentApi, fetchByProject, wrapper };
}

describe('project storage environment frontend contract', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
  });

  it('maps project-scoped CRUD methods to the B1 REST paths', async () => {
    const { default: BaseApi } = await import('@/api/support/base-api');
    const get = vi.spyOn(BaseApi.prototype, 'get').mockResolvedValue({
      content: [],
      total: 0,
    });
    const post = vi.spyOn(BaseApi.prototype, 'post').mockResolvedValue({ id: 7 });
    const put = vi.spyOn(BaseApi.prototype, 'put').mockResolvedValue({ id: 7 });
    const remove = vi.spyOn(BaseApi.prototype, 'delete').mockResolvedValue();
    const { default: environmentApi } = await import('@/api/project-storage-environment-api');
    const payload = {
      name: 'production',
      storage_cluster_id: 3,
      description: 'Production storage',
      is_active: true,
    };

    await environmentApi.fetchByProject(42, { page: 2, size: 20 });
    await environmentApi.createForProject(42, payload);
    await environmentApi.replace(7, { name: 'production-2', is_active: false });
    await environmentApi.deleteById(7);

    expect(get).toHaveBeenCalledWith('/projects/42/storage-environments', {
      page: 2,
      size: 20,
    });
    expect(post).toHaveBeenCalledWith('/projects/42/storage-environments', payload);
    expect(put).toHaveBeenCalledWith('/storage-environments/7', {
      name: 'production-2',
      is_active: false,
    });
    expect(remove).toHaveBeenCalledWith('/storage-environments/7');
  });

  it('adds the storage environment entry to the existing project detail page', async () => {
    const { default: ProjectDetailPage } = await import('@/pages/project/ProjectDetailPage.vue');
    const ProjectStorageEnvironmentTable = defineComponent({
      name: 'ProjectStorageEnvironmentTable',
      props: { projectId: Number },
      setup() {
        return () => h('section', '存储环境');
      },
    });
    const wrapper = shallowMount(ProjectDetailPage, {
      global: {
        stubs: {
          RealTimePage: true,
          ProjectStorageEnvironmentTable,
        },
      },
    });

    await flushPromises();

    const environmentTable = wrapper.findComponent(ProjectStorageEnvironmentTable);
    expect(wrapper.text()).toContain('存储环境');
    expect(environmentTable.exists()).toBe(true);
    expect(environmentTable.props('projectId')).toBe(42);
  });

  it('loads {content,total}, paginates, and never references cluster credentials', async () => {
    const { fetchByProject, wrapper } = await mountEnvironmentTable({
      content: [
        {
          id: 7,
          name: 'production',
          storage_cluster: {
            id: 3,
            name: 'cluster-a',
            storage_type: 'netapp',
          },
        },
      ],
      total: 21,
    });

    const table = wrapper.findComponent(DataTableStub);
    expect(fetchByProject).toHaveBeenCalledWith(42, expect.objectContaining({
      page: 1,
      size: 20,
    }));
    expect(table.props('data')).toHaveLength(1);
    expect(table.props('pagination')).toEqual(expect.objectContaining({ total: 21 }));

    table.vm.$emit('update:pagination', { page: 2, pageSize: 10 });
    await flushPromises();
    expect(fetchByProject).toHaveBeenLastCalledWith(42, expect.objectContaining({
      page: 2,
      size: 10,
    }));

    const source = readFileSync(
      fileURLToPath(new URL('../../src/pages/project/components/ProjectStorageEnvironmentTable.vue', import.meta.url)),
      'utf8',
    );
    expect(source).not.toMatch(/storage_host|storage_user|storage_password/);
  });

  it('renders explicit empty and load-error states', async () => {
    const empty = await mountEnvironmentTable({ content: [], total: 0 });
    expect(empty.wrapper.text()).toMatch(/暂无.*存储环境/);

    empty.wrapper.unmount();
    vi.restoreAllMocks();

    const failed = await mountEnvironmentTable(new Error('network unavailable'));
    expect(failed.wrapper.text()).toMatch(/加载.*失败/);
  });

  it('requires a second confirmation and explains a linked-group 409', async () => {
    const { ElMessage, ElMessageBox } = await import('element-plus');
    const confirm = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue();
    const messageError = vi.spyOn(ElMessage, 'error').mockImplementation(() => {});
    const { environmentApi, wrapper } = await mountEnvironmentTable({
      content: [{ id: 7, name: 'production', storage_cluster: { id: 3, name: 'cluster-a' } }],
      total: 1,
    });
    vi.spyOn(environmentApi, 'deleteById').mockRejectedValue({
      response: {
        status: 409,
        data: { detail: 'environment has linked group' },
      },
    });

    const deleteButton = wrapper.findAll('button').find((button) => button.text() === '删除');
    expect(deleteButton).toBeTruthy();
    await deleteButton.trigger('click');
    await flushPromises();

    expect(confirm).toHaveBeenCalledWith(
      expect.stringMatching(/production.*(确认|删除)|(?:确认|删除).*production/),
      expect.anything(),
      expect.anything(),
    );
    expect(environmentApi.deleteById).toHaveBeenCalledWith(7);
    const friendlyMessage = JSON.stringify(messageError.mock.calls);
    expect(friendlyMessage).toContain('项目组');
    expect(friendlyMessage).toContain('无法删除');
  });

  it('validates create/edit fields and trims names before submitting', async () => {
    const { default: environmentApi } = await import('@/api/project-storage-environment-api');
    const createForProject = vi.spyOn(environmentApi, 'createForProject').mockResolvedValue({ id: 7 });
    const replace = vi.spyOn(environmentApi, 'replace').mockResolvedValue({ id: 7 });
    const { default: ProjectStorageEnvironmentFormDialog } = await import(
      '@/pages/project/components/ProjectStorageEnvironmentFormDialog.vue'
    );
    const wrapper = shallowMount(ProjectStorageEnvironmentFormDialog, {
      props: { projectId: 42 },
      attachTo: document.body,
      global: {
        stubs: {
          ElButton: ElButtonStub,
          ElDialog: ElDialogStub,
          ElForm: ElFormStub,
          ElFormItem: ElFormItemStub,
          ElInput: true,
          ElOption: true,
          ElSelect: true,
          ElSwitch: true,
          StorageClusterSelect: true,
        },
      },
    });
    const exposed = wrapper.vm.$.exposed;

    expect(typeof exposed.create).toBe('function');
    expect(typeof exposed.edit).toBe('function');

    exposed.create();
    await nextTick();
    let form = wrapper.findComponent(ElFormStub);
    const fieldProps = wrapper.findAllComponents(ElFormItemStub).map((item) => item.props('prop'));
    expect(fieldProps).toEqual(expect.arrayContaining([
      'name',
      'storage_cluster_id',
      'description',
      'is_active',
    ]));
    expect(form.props('rules').name).toEqual(expect.arrayContaining([
      expect.objectContaining({ required: true }),
      expect.objectContaining({ max: 128 }),
    ]));
    expect(form.props('rules').storage_cluster_id).toEqual(expect.arrayContaining([
      expect.objectContaining({ required: true }),
    ]));

    Object.assign(form.props('model'), {
      name: '  production  ',
      storage_cluster_id: 3,
      description: 'Production storage',
      is_active: true,
    });
    await wrapper.findAll('button').find((button) => button.text() === '提交').trigger('click');
    await flushPromises();
    expect(createForProject).toHaveBeenCalledWith(42, {
      name: 'production',
      storage_cluster_id: 3,
      description: 'Production storage',
      is_active: true,
    });

    exposed.edit({
      id: 7,
      project_id: 42,
      storage_cluster_id: 3,
      name: 'production',
      description: 'Production storage',
      is_active: true,
    });
    await nextTick();
    form = wrapper.findComponent(ElFormStub);
    Object.assign(form.props('model'), {
      name: '  production-renamed  ',
      description: null,
      is_active: false,
    });
    await wrapper.findAll('button').find((button) => button.text() === '提交').trigger('click');
    await flushPromises();
    expect(replace).toHaveBeenCalledWith(7, {
      name: 'production-renamed',
      description: null,
      is_active: false,
    });

    const source = readFileSync(
      fileURLToPath(new URL('../../src/pages/project/components/ProjectStorageEnvironmentFormDialog.vue', import.meta.url)),
      'utf8',
    );
    expect(source).not.toMatch(/storage_host|storage_user|storage_password/);
  });
});
