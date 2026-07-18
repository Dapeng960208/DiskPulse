import { defineComponent, h } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const membershipApi = vi.hoisted(() => ({
  create: vi.fn(),
  list: vi.fn(),
  remove: vi.fn(),
  update: vi.fn(),
}));
const ui = vi.hoisted(() => ({
  confirm: vi.fn(),
  error: vi.fn(),
  success: vi.fn(),
}));

vi.mock('@/api/project-membership-api.js', () => ({ default: membershipApi }));
vi.mock('@/components/form/RdUserSelect.vue', () => ({
  default: defineComponent({
    name: 'RdUserSelect',
    emits: ['update:modelValue'],
    setup(_props, { emit }) {
      return () => h('button', { class: 'user-select', onClick: () => emit('update:modelValue', 2) });
    },
  }),
}));
vi.mock('element-plus', () => ({
  ElButton: { name: 'ElButton', template: '<button><slot /></button>' },
  ElDialog: {
    name: 'ElDialog',
    props: { modelValue: Boolean, appendToBody: Boolean },
    template: '<div v-if="modelValue" class="member-dialog"><slot /><slot name="footer" /></div>',
  },
  ElForm: { name: 'ElForm', template: '<form><slot /></form>' },
  ElFormItem: { name: 'ElFormItem', template: '<div><slot /></div>' },
  ElMessage: { error: ui.error, success: ui.success, warning: vi.fn() },
  ElMessageBox: { confirm: ui.confirm },
  ElOption: { name: 'ElOption', template: '<option><slot /></option>' },
  ElSelect: { name: 'ElSelect', template: '<select><slot /></select>' },
  ElTable: { name: 'ElTable', template: '<div><slot /></div>' },
  ElTableColumn: {
    name: 'ElTableColumn',
    template: '<div><slot :row="{ user_id: 7, role: \'reader\', user: { rd_username: \'alice\' } }" /></div>',
  },
  ElTag: { name: 'ElTag', template: '<span><slot /></span>' },
}));

import ProjectMembersTab from '@/pages/project/components/ProjectMembersTab.vue';

async function mountTab() {
  const wrapper = mount(ProjectMembersTab, {
    props: { projectId: 1, canManageProjectAdmins: false },
    global: {
      directives: { loading: () => undefined },
    },
  });
  await flushPromises();
  return wrapper;
}

const findButton = (wrapper, label) => wrapper.findAll('button').find((button) => button.text() === label);

describe('ProjectMembersTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    membershipApi.list.mockResolvedValue([{ user_id: 7, role: 'reader', user: { rd_username: 'alice' } }]);
  });

  it('shows an error when adding a member fails instead of leaving a rejected promise', async () => {
    membershipApi.create.mockRejectedValue(new Error('forbidden'));
    const wrapper = await mountTab();

    await findButton(wrapper, '添加成员').trigger('click');
    await wrapper.find('.user-select').trigger('click');
    await findButton(wrapper, '保存').trigger('click');
    await flushPromises();

    expect(membershipApi.create).toHaveBeenCalledWith(1, { user_id: 2, role: 'reader' });
    expect(ui.error).toHaveBeenCalledWith('保存项目成员失败，请稍后重试');
  });

  it('opens the add-member form above the project tabs', async () => {
    const wrapper = await mountTab();

    expect(wrapper.find('.member-dialog').exists()).toBe(false);
    await findButton(wrapper, '添加成员').trigger('click');

    expect(wrapper.find('.member-dialog').exists()).toBe(true);
    expect(wrapper.findComponent({ name: 'ElDialog' }).props('appendToBody')).toBe(true);
  });

  it('shows an error when confirmed removal fails instead of treating it as cancellation', async () => {
    ui.confirm.mockResolvedValue();
    membershipApi.remove.mockRejectedValue(new Error('network'));
    const wrapper = await mountTab();

    await findButton(wrapper, '移除').trigger('click');
    await flushPromises();

    expect(membershipApi.remove).toHaveBeenCalledWith(1, 7);
    expect(ui.error).toHaveBeenCalledWith('移除项目成员失败，请稍后重试');
  });
});
