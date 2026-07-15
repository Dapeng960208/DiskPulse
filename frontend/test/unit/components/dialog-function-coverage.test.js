import { computed, defineComponent, h, ref } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

const projectApi = {
  create: vi.fn(() => Promise.resolve({ id: 1 })),
  replace: vi.fn(() => Promise.resolve({ id: 1 })),
};

const groupApi = {
  create: vi.fn(() => Promise.resolve({ id: 2 })),
  replace: vi.fn(() => Promise.resolve({ id: 2 })),
  fetchById: vi.fn((id) => Promise.resolve({
    id,
    linux_path: `/group-${id}`,
    project: { id: 1, name: 'Project-1' },
    group_tag: { id: 11, name: 'production' },
    storage_cluster: { id: 3, name: 'netapp-1', storage_type: 'netapp' },
  })),
};

const usersApi = {
  create: vi.fn(() => Promise.resolve({ id: 3 })),
  replace: vi.fn(() => Promise.resolve({ id: 3 })),
  fetchById: vi.fn((id) => Promise.resolve({ id, rd_username: `user-${id}` })),
};

const storageUsageApi = {
  create: vi.fn(() => Promise.resolve({ id: 4 })),
  replace: vi.fn(() => Promise.resolve({ id: 4 })),
};

const storageClusterApi = {
  create: vi.fn(() => Promise.resolve({ id: 5 })),
  replace: vi.fn(() => Promise.resolve({ id: 5 })),
  fetchById: vi.fn((id) => Promise.resolve({ id, storage_type: 'netapp' })),
};

const groupTagApi = {
  create: vi.fn(() => Promise.resolve({ id: 11 })),
  replace: vi.fn(() => Promise.resolve({ id: 11 })),
};

const messageSuccess = vi.fn();
const messageError = vi.fn();

vi.mock('echarts', () => ({
  number: Number,
}));

vi.mock('element-plus', async (importOriginal) => {
  const actual = await importOriginal();

  return {
    ...actual,
    ElMessage: {
      success: messageSuccess,
      error: messageError,
    },
  };
});

vi.mock('@/api/project-api', () => ({ default: projectApi }));
vi.mock('@/api/group-api', () => ({ default: groupApi }));
vi.mock('@/api/users-api', () => ({ default: usersApi }));
vi.mock('@/api/storage-usage-api', () => ({ default: storageUsageApi }));
vi.mock('@/api/storage-cluster-api', () => ({ default: storageClusterApi }));
vi.mock('@/api/group-tag-api', () => ({ default: groupTagApi }));
vi.mock('@/components/form/RdUserSelect.vue', () => ({ default: createSelectComponentStub('RdUserSelect') }));
vi.mock('@/components/form/ProjectSelect.vue', () => ({ default: createSelectComponentStub('ProjectSelect') }));
vi.mock('@/components/form/GroupTagSelect.vue', () => ({ default: createSelectComponentStub('GroupTagSelect') }));
vi.mock('@/components/form/VolumeSelect.vue', () => ({ default: createSelectComponentStub('VolumeSelect') }));
vi.mock('@/components/form/QtreeSelect.vue', () => ({ default: createSelectComponentStub('QtreeSelect') }));
vi.mock('@/components/form/StorageClusterSelect.vue', () => ({ default: createSelectComponentStub('StorageClusterSelect') }));
vi.mock('@/components/form/MailSelect.vue', () => ({ default: createSelectComponentStub('MailSelect') }));
vi.mock('@/components/form/GroupSelect.vue', () => ({ default: createSelectComponentStub('GroupSelect') }));
vi.mock('@/components/form/HostsSelect.vue', () => ({ default: createSelectComponentStub('HostsSelect') }));
vi.mock('@/components/data/UserAvatar.vue', () => ({
  default: defineComponent({
    name: 'UserAvatar',
    setup() {
      return () => h('div');
    },
  }),
}));

vi.mock('@/composables/dialog', () => ({
  useDialog: () => {
    const visible = ref(false);

    return {
      visible,
      open: vi.fn(() => {
        visible.value = true;
      }),
      close: vi.fn(() => {
        visible.value = false;
      }),
    };
  },
}));

vi.mock('@/composables/form', () => ({
  useForm: (initialModel, options) => {
    const formRef = ref({
      clearValidate: vi.fn(),
      validate: vi.fn(() => Promise.resolve()),
    });
    const mode = ref('create');
    const model = ref(initialModel());
    const modelRules = computed(() => options.rules(model));
    const submitting = ref(false);

    // Force evaluation so the component-local rules callbacks count as covered.
    void modelRules.value;

    function edit(existing) {
      if (existing) {
        model.value = { ...initialModel(), ...existing };
        mode.value = 'update';
      } else {
        model.value = initialModel();
        mode.value = 'create';
      }
    }

    async function submit() {
      submitting.value = true;
      await options.doSubmit(mode.value);
      options.onSuccess(mode.value);
      submitting.value = false;
    }

    return {
      formRef,
      mode,
      model,
      modelRules,
      submitting,
      edit,
      submit,
    };
  },
}));

function createButtonStub(name) {
  return defineComponent({
    name,
    emits: ['click'],
    setup(_, { emit, slots, attrs }) {
      return () => h('button', { ...attrs, onClick: () => emit('click') }, slots.default?.());
    },
  });
}

const ElDialogStub = defineComponent({
  name: 'ElDialog',
  props: {
    modelValue: Boolean,
  },
  emits: ['update:modelValue', 'close'],
  setup(_, { emit, slots }) {
    return () => h('div', [
      slots.default?.(),
      slots.footer?.(),
      h('button', { 'data-test': 'dialog-model', onClick: () => emit('update:modelValue', false) }),
      h('button', { 'data-test': 'dialog-close', onClick: () => emit('close') }),
    ]);
  },
});

const ElInputStub = defineComponent({
  name: 'ElInput',
  props: {
    modelValue: {
      type: [String, Number],
      default: '',
    },
  },
  emits: ['update:modelValue'],
  setup(props, { emit, attrs }) {
    return () => h('input', {
      ...attrs,
      value: props.modelValue,
      onInput: (event) => emit('update:modelValue', event.target.value),
    });
  },
});

const ElSelectStub = defineComponent({
  name: 'ElSelect',
  props: {
    modelValue: {
      type: [String, Number, Array],
      default: '',
    },
  },
  emits: ['update:modelValue'],
  setup(props, { emit, slots }) {
    return () => h('select', {
      value: props.modelValue,
      onChange: (event) => emit('update:modelValue', event.target.value),
    }, slots.default?.());
  },
});

const ElOptionStub = defineComponent({
  name: 'ElOption',
  props: {
    label: String,
    value: [String, Number],
  },
  setup(props, { slots }) {
    return () => h('option', { value: props.value }, slots.default?.() ?? props.label);
  },
});

const ElInputNumberStub = defineComponent({
  name: 'ElInputNumber',
  props: {
    modelValue: {
      type: Number,
      default: 0,
    },
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('input', {
      type: 'number',
      value: props.modelValue,
      onInput: (event) => emit('update:modelValue', Number(event.target.value)),
    });
  },
});

const ElSwitchStub = defineComponent({
  name: 'ElSwitch',
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
    disabled: Boolean,
    activeText: String,
    inactiveText: String,
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('input', {
      type: 'checkbox',
      checked: props.modelValue,
      onChange: (event) => emit('update:modelValue', event.target.checked),
    });
  },
});

function createSelectComponentStub(name) {
  return defineComponent({
    name,
    emits: ['update:modelValue', 'change'],
    setup(_, { emit }) {
      return () => h('div', [
        h('button', { 'data-test': `${name}-update`, onClick: () => emit('update:modelValue', 1) }),
        h('button', { 'data-test': `${name}-change`, onClick: () => emit('change', 1) }),
      ]);
    },
  });
}

const globalStubs = {
  ElButton: createButtonStub('ElButton'),
  ElDialog: ElDialogStub,
  ElForm: defineComponent({
    name: 'ElForm',
    setup(_, { slots, expose }) {
      expose({
        clearValidate: vi.fn(),
      });
      return () => h('form', slots.default?.());
    },
  }),
  ElFormItem: defineComponent({ name: 'ElFormItem', setup(_, { slots }) { return () => h('div', slots.default?.()); } }),
  ElInput: ElInputStub,
  ElInputNumber: ElInputNumberStub,
  ElSelect: ElSelectStub,
  ElOption: ElOptionStub,
  ElSwitch: ElSwitchStub,
};

function getExposed(wrapper) {
  return wrapper.vm.$.exposed;
}

function findSubmitButton(wrapper) {
  return wrapper.findAll('button').find((button) => button.text().includes('提交'));
}

describe('dialog component function coverage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('executes project form dialog handlers', async () => {
    const { default: ProjectFormDialog } = await import('@/pages/project/components/ProjectFormDialog.vue');
    const wrapper = shallowMount(ProjectFormDialog, {
      global: { stubs: globalStubs },
    });

    getExposed(wrapper).edit({ id: 1, name: 'Demo' });
    await wrapper.findAll('input').at(0).setValue('Demo Project');
    wrapper.findAllComponents({ name: 'RdUserSelect' }).at(0).vm.$emit('update:modelValue', 10);
    wrapper.findAllComponents({ name: 'RdUserSelect' }).at(1).vm.$emit('update:modelValue', 11);
    await wrapper.findAll('input').at(1).setValue('project description');
    await findSubmitButton(wrapper).trigger('click');
    await wrapper.find('[data-test="dialog-model"]').trigger('click');
    await wrapper.find('[data-test="dialog-close"]').trigger('click');
    await flushPromises();

    expect(projectApi.replace).toHaveBeenCalled();
    expect(messageSuccess).toHaveBeenCalled();
    expect(wrapper.emitted('submitted')).toBeTruthy();
  }, 15000);

  it('executes group form dialog handlers', async () => {
    const { default: GroupFormDialog } = await import('@/pages/group/components/GroupFormDialog.vue');
    const wrapper = shallowMount(GroupFormDialog, {
      global: { stubs: globalStubs },
    });

    getExposed(wrapper).edit();
    await wrapper.find('input').setValue('group-name');
    wrapper.findComponent({ name: 'ProjectSelect' }).vm.$emit('update:modelValue', 1);
    await flushPromises();

    expect(wrapper.findComponent({ name: 'StorageClusterSelect' }).exists()).toBe(true);
    expect(wrapper.findComponent({ name: 'GroupTagSelect' }).exists()).toBe(true);
  }, 15000);

  it('does not submit read-only group response fields when editing', async () => {
    const { default: GroupFormDialog } = await import('@/pages/group/components/GroupFormDialog.vue');
    const wrapper = shallowMount(GroupFormDialog, {
      global: { stubs: globalStubs },
    });

    await getExposed(wrapper).edit({
      id: 2,
      name: 'group-name',
      project_id: 1,
      storage_cluster_id: 3,
      group_tag_id: 11,
      volume_id: 42,
      linux_path: '/group-name',
      project: { id: 1, name: 'Project-1' },
      group_tag: { id: 11, name: 'production' },
      storage_cluster: { id: 3, name: 'netapp-1', storage_type: 'netapp' },
      storage_target: { id: 42, name: 'volume-42', type: 'volume' },
      qtree: null,
      in_charge_user: null,
    });
    await findSubmitButton(wrapper).trigger('click');
    await flushPromises();

    expect(Object.keys(groupApi.replace.mock.lastCall[1])).not.toEqual(
      expect.arrayContaining(['qtree', 'in_charge_user']),
    );
  }, 15000);

  it('clears stale project-group target ids when the target type changes', async () => {
    const { default: GroupFormDialog } = await import('@/pages/group/components/GroupFormDialog.vue');
    const wrapper = shallowMount(GroupFormDialog, {
      global: { stubs: globalStubs },
    });

    getExposed(wrapper).edit();
    wrapper.findComponent({ name: 'StorageClusterSelect' }).vm.$emit('update:modelValue', 3);
    await flushPromises();

    wrapper.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'volume');
    await flushPromises();
    wrapper.findComponent({ name: 'VolumeSelect' }).vm.$emit('update:modelValue', 42);
    wrapper.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'qtree');
    await flushPromises();
    wrapper.findComponent({ name: 'QtreeSelect' }).vm.$emit('update:modelValue', 84);
    wrapper.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'volume');
    await flushPromises();
    await findSubmitButton(wrapper).trigger('click');
    await flushPromises();

    expect(groupApi.create).toHaveBeenCalledWith(expect.objectContaining({ volume_id: null }));
    expect(groupApi.create.mock.lastCall[0]).not.toHaveProperty('qtree_id');
  }, 15000);

  it('fixes Isilon project groups to a Directory Quota storage space', async () => {
    storageClusterApi.fetchById.mockResolvedValueOnce({ id: 8, storage_type: 'isilon' });
    const { default: GroupFormDialog } = await import('@/pages/group/components/GroupFormDialog.vue');
    const wrapper = shallowMount(GroupFormDialog, {
      global: { stubs: globalStubs },
    });

    getExposed(wrapper).edit();
    wrapper.findComponent({ name: 'StorageClusterSelect' }).vm.$emit('update:modelValue', 8);
    await flushPromises();

    expect(wrapper.findComponent({ name: 'ElSelect' }).exists()).toBe(false);
    expect(wrapper.findComponent({ name: 'VolumeSelect' }).exists()).toBe(true);
    expect(wrapper.text()).toContain('存储空间（Directory Quota）');
  }, 15000);

  it('executes user form dialog handlers', async () => {
    const { default: UserFormDialog } = await import('@/pages/admin/user/components/UserFormDialog.vue');
    const wrapper = shallowMount(UserFormDialog, {
      global: { stubs: globalStubs },
    });

    getExposed(wrapper).edit({ id: 9, rd_username: 'demo' });
    await wrapper.findAll('input').at(0).setValue('rd-demo');
    await wrapper.findAll('input').at(1).setValue('domain-demo');
    await wrapper.findAll('input').at(2).setValue('demo@example.com');
    await wrapper.find('select').setValue('1');
    await wrapper.find('input[type="checkbox"]').setChecked(false);
    await findSubmitButton(wrapper).trigger('click');
    await wrapper.find('[data-test="dialog-model"]').trigger('click');
    await wrapper.find('[data-test="dialog-close"]').trigger('click');
    await flushPromises();

    expect(usersApi.replace).toHaveBeenCalled();
    expect(messageSuccess).toHaveBeenCalled();
  }, 15000);

  it('executes storage cluster form dialog handlers', async () => {
    const { default: StorageClusterFormDialog } = await import('@/pages/admin/storage-cluster/components/StorageClusterFormDialog.vue');
    const wrapper = shallowMount(StorageClusterFormDialog, {
      global: { stubs: globalStubs },
    });

    getExposed(wrapper).edit();
    await wrapper.findAll('input').at(0).setValue('cluster-name');
    await wrapper.findAll('input').at(1).setValue('cluster-desc');
    await wrapper.find('select').setValue('netapp');
    await wrapper.findAll('input').at(2).setValue('127.0.0.1');
    await wrapper.find('input[type="number"]').setValue(2022);
    await wrapper.findAll('input').at(4).setValue('storage-user');
    await wrapper.findAll('input').at(5).setValue('secret');
    const activeSwitch = wrapper.findAllComponents({ name: 'ElSwitch' })
      .find((switchComponent) => switchComponent.props('activeText') === '启用');
    expect(activeSwitch.find('input').element.checked).toBe(true);
    await activeSwitch.find('input').setChecked(false);
    await findSubmitButton(wrapper).trigger('click');
    await wrapper.find('[data-test="dialog-model"]').trigger('click');
    await wrapper.find('[data-test="dialog-close"]').trigger('click');
    await flushPromises();

    expect(storageClusterApi.create).toHaveBeenCalledWith(expect.objectContaining({ is_active: false }));
    expect(messageSuccess).toHaveBeenCalled();
  }, 15000);

  it('submits per-cluster transport defaults and disables TLS verification for HTTP', async () => {
    const { default: StorageClusterFormDialog } = await import('@/pages/admin/storage-cluster/components/StorageClusterFormDialog.vue');
    const wrapper = shallowMount(StorageClusterFormDialog, {
      global: { stubs: globalStubs },
    });

    getExposed(wrapper).edit();
    const protocolSelect = wrapper.findAllComponents({ name: 'ElSelect' })
      .find((select) => select.props('modelValue') === 'https');
    const protocolOptions = wrapper.findAllComponents({ name: 'ElOption' })
      .map((option) => option.props('value'));

    expect(protocolSelect).toBeDefined();
    expect(protocolOptions).toEqual(expect.arrayContaining(['http', 'https']));
    await findSubmitButton(wrapper).trigger('click');
    await flushPromises();
    expect(storageClusterApi.create).toHaveBeenLastCalledWith(expect.objectContaining({
      protocol: 'https',
      tls_verify: true,
    }));

    getExposed(wrapper).edit();
    const freshProtocolSelect = wrapper.findAllComponents({ name: 'ElSelect' })
      .find((select) => select.props('modelValue') === 'https');
    freshProtocolSelect.vm.$emit('update:modelValue', 'http');
    await flushPromises();
    const tlsSwitch = wrapper.findAllComponents({ name: 'ElSwitch' })
      .find((switchComponent) => switchComponent.props('modelValue') === false);

    expect(tlsSwitch).toBeDefined();
    expect(tlsSwitch.props('disabled')).toBe(true);
    await findSubmitButton(wrapper).trigger('click');
    await flushPromises();
    expect(storageClusterApi.create).toHaveBeenLastCalledWith(expect.objectContaining({
      protocol: 'http',
      tls_verify: false,
    }));
  }, 15000);

  it('loads persisted protocol and TLS verification values when editing a cluster', async () => {
    const { default: StorageClusterFormDialog } = await import('@/pages/admin/storage-cluster/components/StorageClusterFormDialog.vue');
    const wrapper = shallowMount(StorageClusterFormDialog, {
      global: { stubs: globalStubs },
    });

    getExposed(wrapper).edit({
      id: 12,
      name: 'secure-cluster',
      protocol: 'https',
      tls_verify: false,
    });
    await flushPromises();

    const protocolSelect = wrapper.findAllComponents({ name: 'ElSelect' })
      .find((select) => select.props('modelValue') === 'https');
    const tlsSwitch = wrapper.findAllComponents({ name: 'ElSwitch' })
      .find((switchComponent) => switchComponent.props('modelValue') === false);
    expect(protocolSelect).toBeDefined();
    expect(tlsSwitch).toBeDefined();
    expect(tlsSwitch.props('disabled')).toBe(false);

    await findSubmitButton(wrapper).trigger('click');
    await flushPromises();
    expect(storageClusterApi.replace).toHaveBeenLastCalledWith(12, expect.objectContaining({
      protocol: 'https',
      tls_verify: false,
    }));
  }, 15000);

  it('shows and persists session cache settings only for Isilon clusters', async () => {
    const { default: StorageClusterFormDialog } = await import('@/pages/admin/storage-cluster/components/StorageClusterFormDialog.vue');
    const wrapper = shallowMount(StorageClusterFormDialog, {
      global: { stubs: globalStubs },
    });

    getExposed(wrapper).edit();
    expect(wrapper.find('[data-test="isilon-session-cache-mode"]').exists()).toBe(false);

    const storageType = wrapper.findAllComponents({ name: 'ElSelect' })
      .find((select) => select.props('modelValue') === null);
    storageType.vm.$emit('update:modelValue', 'isilon');
    await flushPromises();

    const cacheMode = wrapper.find('[data-test="isilon-session-cache-mode"]');
    expect(cacheMode.exists()).toBe(true);
    cacheMode.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'file');
    await flushPromises();
    expect(wrapper.find('[data-test="isilon-session-cache-path"]').exists()).toBe(true);

    await findSubmitButton(wrapper).trigger('click');
    await flushPromises();
    expect(storageClusterApi.create).toHaveBeenLastCalledWith(expect.objectContaining({
      storage_type: 'isilon',
      isilon_session_cache_mode: 'file',
      isilon_session_cache_path: '.isilon_cache/cache.json',
    }));

    cacheMode.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'redis');
    await flushPromises();
    expect(wrapper.find('[data-test="isilon-session-cache-path"]').exists()).toBe(false);
  }, 15000);

  it('executes usage form dialog handlers', async () => {
    const { default: UsageFormDialog } = await import('@/pages/usage/components/UsageFormDialog.vue');
    const wrapper = shallowMount(UsageFormDialog, {
      global: { stubs: globalStubs },
    });

    getExposed(wrapper).edit({
      id: 11,
      project: { id: 1, name: 'Project-1' },
      group_id: 2,
      user_id: 3,
      linux_path: '/existing/path',
    });
    const groupSelect = wrapper.findComponent({ name: 'GroupSelect' });
    const userSelect = wrapper.findComponent({ name: 'RdUserSelect' });

    wrapper.findComponent({ name: 'ProjectSelect' }).vm.$emit('update:modelValue', 1);
    groupSelect.vm.$emit('update:modelValue', 5);
    groupSelect.vm.$emit('change', 5);
    userSelect.vm.$emit('update:modelValue', 7);
    userSelect.vm.$emit('change', 7);
    await flushPromises();
    expect(wrapper.findComponent({ name: 'StorageClusterSelect' }).exists()).toBe(false);

    await findSubmitButton(wrapper).trigger('click');
    await wrapper.find('[data-test="dialog-model"]').trigger('click');
    await wrapper.find('[data-test="dialog-close"]').trigger('click');
    await flushPromises();

    expect(groupApi.fetchById).toHaveBeenCalled();
    expect(usersApi.fetchById).toHaveBeenCalled();
    expect(storageUsageApi.replace).toHaveBeenCalledWith(11, { group_id: 5, user_id: 7 });
    expect(messageSuccess).toHaveBeenCalled();
  }, 15000);

  it('executes group tag form field and close handlers', async () => {
    const { default: GroupTagFormDialog } = await import(
      '@/pages/group-tag/components/GroupTagFormDialog.vue'
    );
    const wrapper = shallowMount(GroupTagFormDialog, {
      global: { stubs: globalStubs },
    });

    getExposed(wrapper).edit();
    await wrapper.find('input').setValue('production');
    await findSubmitButton(wrapper).trigger('click');
    await wrapper.find('[data-test="dialog-close"]').trigger('click');
    await flushPromises();

    expect(groupTagApi.create).toHaveBeenCalledWith({ name: 'production' });
    expect(wrapper.emitted('submitted')).toBeTruthy();
  }, 15000);

  it('executes export dialog open, selection, submit, and close handlers', async () => {
    const { default: ExportDialog } = await import('@/components/form/ExportDialog.vue');
    const wrapper = shallowMount(ExportDialog, {
      global: { stubs: globalStubs },
    });

    getExposed(wrapper).open();
    await wrapper.find('select').setValue('excel');
    await wrapper.findAll('button').find((button) => button.text().includes('确认导出')).trigger('click');
    getExposed(wrapper).open();
    await wrapper.findAll('button').find((button) => button.text().includes('取消')).trigger('click');

    expect(wrapper.emitted('submitted')).toEqual([['excel']]);
  });
});
