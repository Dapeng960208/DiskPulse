import { defineComponent, h } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  apis: {
    group: {
      create: vi.fn(() => Promise.resolve({ id: 1 })),
      replace: vi.fn(() => Promise.resolve({ id: 1 })),
      fetchById: vi.fn(() => Promise.resolve({ id: 7, linux_path: 'team', project: { id: 3 } })),
    },
    project: {
      create: vi.fn(() => Promise.resolve({ id: 3 })),
      replace: vi.fn(() => Promise.resolve({ id: 3 })),
      fetchById: vi.fn(() => Promise.resolve({ id: 3, storage_alert_rule: { enabled: true } })),
    },
    config: {
      fetch: vi.fn(() => Promise.resolve({ storage_alert_rule: { enabled: true } })),
    },
    storageCluster: {
      create: vi.fn(() => Promise.resolve({ id: 8 })),
      replace: vi.fn(() => Promise.resolve({ id: 8 })),
      fetchById: vi.fn(() => Promise.resolve({ id: 8, storage_type: 'netapp' })),
    },
    groupTag: {
      create: vi.fn(() => Promise.resolve({ id: 4 })),
      replace: vi.fn(() => Promise.resolve({ id: 4 })),
    },
    users: {
      create: vi.fn(() => Promise.resolve({ id: 5 })),
      replace: vi.fn(() => Promise.resolve({ id: 5 })),
      fetchById: vi.fn(() => Promise.resolve({ id: 5, rd_username: 'rd-user' })),
    },
    storageUsage: {
      create: vi.fn(() => Promise.resolve({ id: 6 })),
      replace: vi.fn(() => Promise.resolve({ id: 6 })),
    },
  },
  message: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('element-plus', () => {
  const passthrough = (name, tag = 'div') => defineComponent({
    name,
    inheritAttrs: false,
    setup(_, { attrs, slots }) {
      return () => h(tag, attrs, slots.default?.());
    },
  });
  const ElForm = defineComponent({
    name: 'ElForm',
    setup(_, { expose, slots }) {
      const validate = vi.fn(() => Promise.resolve());
      const clearValidate = vi.fn();
      expose({ validate, clearValidate });
      return () => h('form', slots.default?.());
    },
  });
  const ElButton = passthrough('ElButton', 'button');
  const ElDialog = defineComponent({
    name: 'ElDialog',
    inheritAttrs: false,
    setup(_, { attrs, slots }) {
      return () => h('section', attrs, [
        slots.header?.(),
        slots.default?.(),
        slots.footer?.(),
      ]);
    },
  });
  const ElSelect = defineComponent({
    name: 'ElSelect',
    props: { modelValue: { type: [String, Number, Array], default: null } },
    emits: ['update:modelValue'],
    setup(props, { attrs, slots }) {
      return () => h('select', { ...attrs, value: props.modelValue }, slots.default?.());
    },
  });
  const ElSwitch = defineComponent({
    name: 'ElSwitch',
    props: { modelValue: { type: [Boolean, String, Number], default: false } },
    emits: ['update:modelValue'],
    setup(props, { attrs }) {
      return () => h('button', { ...attrs, type: 'button', 'aria-pressed': String(props.modelValue) });
    },
  });
  const ElInput = defineComponent({
    name: 'ElInput',
    props: { modelValue: { type: [String, Number], default: '' } },
    emits: ['update:modelValue'],
    setup(props, { attrs }) {
      return () => h('input', { ...attrs, value: props.modelValue });
    },
  });
  return {
    ElAlert: passthrough('ElAlert'),
    ElButton,
    ElDialog,
    ElForm,
    ElFormItem: passthrough('ElFormItem'),
    ElInput,
    ElInputNumber: ElInput,
    ElMessage: mocks.message,
    ElOption: passthrough('ElOption', 'option'),
    ElSelect,
    ElSwitch,
  };
});

vi.mock('@/api/group-api', () => ({ default: mocks.apis.group }));
vi.mock('@/api/project-api', () => ({ default: mocks.apis.project }));
vi.mock('@/api/config-api', () => ({ default: mocks.apis.config }));
vi.mock('@/api/storage-cluster-api', () => ({ default: mocks.apis.storageCluster }));
vi.mock('@/api/group-tag-api', () => ({ default: mocks.apis.groupTag }));
vi.mock('@/api/users-api', () => ({ default: mocks.apis.users }));
vi.mock('@/api/storage-usage-api', () => ({ default: mocks.apis.storageUsage }));

const eventStub = (name, events = []) => defineComponent({
  name,
  props: { modelValue: { type: [String, Number, Array, Object, Boolean], default: null } },
  emits: events,
  setup(_, { slots }) {
    return () => h('div', slots.default?.());
  },
});

const formStubs = {
  GroupTagSelect: eventStub('GroupTagSelect', ['update:modelValue', 'selected-label-change']),
  MailSelect: eventStub('MailSelect', ['update:modelValue']),
  ProjectSelect: eventStub('ProjectSelect', ['update:modelValue']),
  QtreeSelect: eventStub('QtreeSelect', ['update:modelValue']),
  RdUserSelect: eventStub('RdUserSelect', ['update:modelValue', 'change']),
  StorageAlertRuleForm: eventStub('StorageAlertRuleForm', ['update:modelValue', 'validity-change']),
  StorageClusterSelect: eventStub('StorageClusterSelect', ['update:modelValue']),
  VolumeSelect: eventStub('VolumeSelect', ['update:modelValue']),
  GroupSelect: eventStub('GroupSelect', ['update:modelValue', 'change']),
};

const mountOptions = () => ({ global: { stubs: formStubs } });

function buttonWithText(wrapper, text) {
  return wrapper.findAll('button').find((button) => button.text().includes(text));
}

describe('form dialogs follow create, update, and dependency-change paths', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.apis.group.create.mockResolvedValue({ id: 1 });
    mocks.apis.group.replace.mockResolvedValue({ id: 1 });
    mocks.apis.group.fetchById.mockResolvedValue({ id: 7, linux_path: 'team', project: { id: 3 } });
    mocks.apis.project.create.mockResolvedValue({ id: 3 });
    mocks.apis.project.replace.mockResolvedValue({ id: 3 });
    mocks.apis.project.fetchById.mockResolvedValue({ id: 3, storage_alert_rule: { enabled: true } });
    mocks.apis.config.fetch.mockResolvedValue({ storage_alert_rule: { enabled: true } });
    mocks.apis.storageCluster.create.mockResolvedValue({ id: 8 });
    mocks.apis.storageCluster.replace.mockResolvedValue({ id: 8 });
    mocks.apis.storageCluster.fetchById.mockResolvedValue({ id: 8, storage_type: 'netapp' });
    mocks.apis.groupTag.create.mockResolvedValue({ id: 4 });
    mocks.apis.groupTag.replace.mockResolvedValue({ id: 4 });
    mocks.apis.users.create.mockResolvedValue({ id: 5 });
    mocks.apis.users.replace.mockResolvedValue({ id: 5 });
    mocks.apis.users.fetchById.mockResolvedValue({ id: 5, rd_username: 'rd-user' });
    mocks.apis.storageUsage.create.mockResolvedValue({ id: 6 });
    mocks.apis.storageUsage.replace.mockResolvedValue({ id: 6 });
  });

  it('creates a group through project, cluster, target, and alert selections', async () => {
    const { default: Dialog } = await import('@/pages/group/components/GroupFormDialog.vue');
    const wrapper = mount(Dialog, mountOptions());

    wrapper.vm.edit();
    await flushPromises();
    await wrapper.findComponent({ name: 'ProjectSelect' }).vm.$emit('update:modelValue', 3);
    await wrapper.findComponent({ name: 'StorageClusterSelect' }).vm.$emit('update:modelValue', 8);
    await wrapper.findComponent({ name: 'GroupTagSelect' }).vm.$emit('update:modelValue', 5);
    await flushPromises();
    await wrapper.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'volume');
    const switches = wrapper.findAllComponents({ name: 'ElSwitch' });
    await switches[1].vm.$emit('update:modelValue', true);
    await wrapper.findComponent({ name: 'StorageAlertRuleForm' }).vm.$emit('validity-change', true);

    await buttonWithText(wrapper, '创建项目组').trigger('click');
    await flushPromises();

    expect(mocks.apis.group.create).toHaveBeenCalledWith(expect.objectContaining({
      project_id: 3,
      storage_cluster_id: 8,
      group_tag_id: 5,
      volume_id: null,
    }));
    expect(mocks.apis.group.create.mock.lastCall[0]).not.toHaveProperty('target_type');
    expect(wrapper.emitted('submitted')).toHaveLength(1);
  });

  it('loads existing group fallbacks and updates the existing qtree', async () => {
    mocks.apis.config.fetch.mockRejectedValueOnce(new Error('config unavailable'));
    mocks.apis.project.fetchById.mockRejectedValueOnce(new Error('project unavailable'));
    mocks.apis.storageCluster.fetchById.mockRejectedValueOnce(new Error('cluster unavailable'));
    const { default: Dialog } = await import('@/pages/group/components/GroupFormDialog.vue');
    const wrapper = mount(Dialog, mountOptions());

    wrapper.vm.edit({
      id: 17,
      name: 'existing',
      project_id: 3,
      storage_cluster_id: 8,
      qtree_id: 9,
      project: { id: 3 },
      storage_target: { type: 'qtree' },
    });
    await flushPromises();
    await buttonWithText(wrapper, '保存修改').trigger('click');
    await flushPromises();

    expect(mocks.apis.group.replace).toHaveBeenCalledWith(17, expect.objectContaining({ qtree_id: 9 }));
  });

  it('does not submit read-only group response fields when editing', async () => {
    const { default: Dialog } = await import('@/pages/group/components/GroupFormDialog.vue');
    const wrapper = mount(Dialog, mountOptions());

    wrapper.vm.edit({
      id: 17,
      name: 'existing',
      project_id: 3,
      storage_cluster_id: 8,
      qtree_id: 9,
      project: { id: 3 },
      storage_target: { type: 'qtree' },
      capabilities: { adjust_quota: true },
      capacity: { used: { value: 10, unit: 'GB' } },
    });
    await flushPromises();
    await buttonWithText(wrapper, '保存修改').trigger('click');
    await flushPromises();

    const payload = mocks.apis.group.replace.mock.lastCall[1];
    expect(payload).not.toHaveProperty('capabilities');
    expect(payload).not.toHaveProperty('capacity');
  });

  it('blocks an invalid custom group alert rule before saving', async () => {
    const { default: Dialog } = await import('@/pages/group/components/GroupFormDialog.vue');
    const wrapper = mount(Dialog, mountOptions());

    wrapper.vm.edit();
    await flushPromises();
    await wrapper.findAllComponents({ name: 'ElSwitch' })[2]
      .vm.$emit('update:modelValue', true);
    await flushPromises();

    const ruleForm = wrapper.findComponent({ name: 'StorageAlertRuleForm' });
    expect(ruleForm.exists()).toBe(true);
    await ruleForm.vm.$emit('validity-change', false);
    expect(buttonWithText(wrapper, '创建项目组').attributes('disabled')).toBeDefined();

    await ruleForm.vm.$emit('validity-change', true);
    await buttonWithText(wrapper, '创建项目组').trigger('click');
    await flushPromises();
    expect(mocks.apis.group.create).toHaveBeenCalledWith(expect.objectContaining({
      storage_alert_rule: expect.any(Object),
    }));
  });

  it('reports a failed group save', async () => {
    mocks.apis.group.create.mockRejectedValueOnce(new Error('save failed'));
    const { default: Dialog } = await import('@/pages/group/components/GroupFormDialog.vue');
    const wrapper = mount(Dialog, mountOptions());

    wrapper.vm.edit();
    await flushPromises();
    await buttonWithText(wrapper, '创建项目组').trigger('click');
    await flushPromises();

    expect(mocks.message.error).toHaveBeenCalledWith('保存项目组失败，请稍后重试');
  });

  it('submits project create and update modes and handles alert-rule loading', async () => {
    const { default: Dialog } = await import('@/pages/project/components/ProjectFormDialog.vue');
    const wrapper = mount(Dialog, mountOptions());

    wrapper.vm.edit();
    await flushPromises();
    await wrapper.findAllComponents({ name: 'ElSwitch' })[1].vm.$emit('update:modelValue', true);
    await flushPromises();
    const ruleForm = wrapper.findComponent({ name: 'StorageAlertRuleForm' });
    expect(ruleForm.exists()).toBe(true);
    await ruleForm.vm.$emit('validity-change', false);
    expect(buttonWithText(wrapper, '创建项目').attributes('disabled')).toBeDefined();
    await ruleForm.vm.$emit('validity-change', true);
    await buttonWithText(wrapper, '创建项目').trigger('click');
    await flushPromises();
    expect(mocks.apis.project.create).toHaveBeenCalled();

    mocks.apis.config.fetch.mockRejectedValueOnce(new Error('config unavailable'));
    wrapper.vm.edit({ id: 3, name: 'project', is_alert: false, storage_alert_rule: null });
    await flushPromises();
    await buttonWithText(wrapper, '保存修改').trigger('click');
    await flushPromises();
    expect(mocks.apis.project.replace).toHaveBeenCalledWith(3, expect.objectContaining({ is_alert: false }));

    mocks.apis.project.replace.mockRejectedValueOnce(new Error('save failed'));
    wrapper.vm.edit({ id: 3, name: 'project', is_alert: true, storage_alert_rule: null });
    await flushPromises();
    await buttonWithText(wrapper, '保存修改').trigger('click');
    await flushPromises();
    expect(mocks.message.error).toHaveBeenCalledWith('保存项目失败，请稍后重试');
  });

  it('creates, updates, and reports a failed group-tag save', async () => {
    const { default: Dialog } = await import('@/pages/group-tag/components/GroupTagFormDialog.vue');
    const wrapper = mount(Dialog, mountOptions());

    wrapper.vm.edit();
    await buttonWithText(wrapper, '创建标签').trigger('click');
    await flushPromises();
    expect(mocks.apis.groupTag.create).toHaveBeenCalledWith({ name: '' });

    wrapper.vm.edit({ id: 4, name: 'core' });
    await flushPromises();
    await buttonWithText(wrapper, '保存修改').trigger('click');
    await flushPromises();
    expect(mocks.apis.groupTag.replace).toHaveBeenCalledWith(4, { name: 'core' });

    mocks.apis.groupTag.replace.mockRejectedValueOnce(new Error('save failed'));
    await buttonWithText(wrapper, '保存修改').trigger('click');
    await flushPromises();
    expect(mocks.message.error).toHaveBeenCalledWith('保存项目组标签失败，请稍后重试');
  });

  it('builds user-directory paths and rejects a group from another project', async () => {
    const { default: Dialog } = await import('@/pages/usage/components/UsageFormDialog.vue');
    const wrapper = mount(Dialog, mountOptions());

    wrapper.vm.edit();
    await wrapper.findComponent({ name: 'ProjectSelect' }).vm.$emit('update:modelValue', 3);
    mocks.apis.group.fetchById.mockResolvedValueOnce({ id: 7, linux_path: 'team', project: { id: 99 } });
    await wrapper.findComponent({ name: 'GroupSelect' }).vm.$emit('change', 7);
    await flushPromises();
    expect(mocks.message.error).toHaveBeenCalledWith('所选项目组不属于当前项目');

    mocks.apis.group.fetchById.mockResolvedValueOnce({
      id: 7,
      linux_path: 'team',
      project: { id: 3 },
      storage_cluster: { name: 'cluster-a' },
    });
    await wrapper.findComponent({ name: 'GroupSelect' }).vm.$emit('change', 7);
    await wrapper.findComponent({ name: 'RdUserSelect' }).vm.$emit('change', 5);
    await flushPromises();
    expect(wrapper.findComponent({ name: 'ElInput' }).props('modelValue')).toBe('team/rd-user');

    await wrapper.findComponent({ name: 'ProjectSelect' }).vm.$emit('update:modelValue', null);
    await wrapper.findComponent({ name: 'GroupSelect' }).vm.$emit('change', null);
    await wrapper.findComponent({ name: 'RdUserSelect' }).vm.$emit('change', null);
    await buttonWithText(wrapper, '创建目录').trigger('click');
    await flushPromises();
    expect(mocks.apis.storageUsage.create).toHaveBeenCalledWith({ group_id: null, user_id: null });
  });

  it('updates an existing user directory and handles group/user lookup failures', async () => {
    mocks.apis.group.fetchById.mockRejectedValueOnce(new Error('group unavailable'));
    mocks.apis.users.fetchById.mockRejectedValueOnce(new Error('user unavailable'));
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const { default: Dialog } = await import('@/pages/usage/components/UsageFormDialog.vue');
    const wrapper = mount(Dialog, mountOptions());

    wrapper.vm.edit({ id: 6, project_id: 3, group_id: 7, user_id: 5, linux_path: 'old/path' });
    await flushPromises();
    await buttonWithText(wrapper, '保存修改').trigger('click');
    await flushPromises();

    expect(mocks.apis.storageUsage.replace).toHaveBeenCalledWith(6, { group_id: 7, user_id: 5 });
    errorSpy.mockRestore();
  });

  it('normalizes account fields for user create and update', async () => {
    const { default: Dialog } = await import('@/pages/admin/user/components/UserFormDialog.vue');
    const wrapper = mount(Dialog, mountOptions());

    wrapper.vm.edit();
    const inputs = wrapper.findAllComponents({ name: 'ElInput' });
    await inputs[0].vm.$emit('update:modelValue', ' rd-user ');
    await inputs[1].vm.$emit('update:modelValue', ' Alice ');
    await inputs[2].vm.$emit('update:modelValue', ' alice@example.com ');
    await inputs[3].vm.$emit('update:modelValue', ' RD ');
    await buttonWithText(wrapper, '创建用户').trigger('click');
    await flushPromises();
    expect(mocks.apis.users.create).toHaveBeenCalledWith(expect.objectContaining({
      rd_username: 'rd-user',
      username: 'Alice',
      email: 'alice@example.com',
      department: 'RD',
    }));

    wrapper.vm.edit({ id: 5, rd_username: 'rd-user', username: 'Alice', email: '', department: '' });
    await flushPromises();
    await buttonWithText(wrapper, '保存修改').trigger('click');
    await flushPromises();
    expect(mocks.apis.users.replace).toHaveBeenCalledWith(5, expect.objectContaining({
      username: 'Alice',
      email: null,
      department: null,
    }));
  });

  it('handles Isilon session settings and storage-cluster create/update', async () => {
    const { default: Dialog } = await import('@/pages/admin/storage-cluster/components/StorageClusterFormDialog.vue');
    const wrapper = mount(Dialog, mountOptions());

    wrapper.vm.edit();
    const selects = wrapper.findAllComponents({ name: 'ElSelect' });
    await selects[0].vm.$emit('update:modelValue', 'isilon');
    await selects[1].vm.$emit('update:modelValue', 'http');
    await flushPromises();
    await wrapper.find('[data-test="isilon-session-cache-mode"]')
      .findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'file');
    expect(wrapper.find('[data-test="isilon-account-help-trigger"]').exists()).toBe(true);
    await wrapper.find('[data-test="isilon-account-help-trigger"]').trigger('click');
    expect(wrapper.find('[data-test="isilon-account-help-dialog"]').exists()).toBe(true);
    await buttonWithText(wrapper, '关闭').trigger('click');

    await buttonWithText(wrapper, '创建集群').trigger('click');
    await flushPromises();
    expect(mocks.apis.storageCluster.create).toHaveBeenCalledWith(expect.objectContaining({
      storage_type: 'isilon',
      protocol: 'http',
      tls_verify: false,
      isilon_session_cache_mode: 'file',
      isilon_session_cache_path: '.isilon_cache/cache.json',
    }));

    wrapper.vm.edit({ id: 8, name: 'cluster-a', storage_type: 'netapp', protocol: 'https' });
    await flushPromises();
    await buttonWithText(wrapper, '保存修改').trigger('click');
    await flushPromises();
    expect(mocks.apis.storageCluster.replace).toHaveBeenCalledWith(8, expect.objectContaining({ storage_type: 'netapp' }));
  });
});
