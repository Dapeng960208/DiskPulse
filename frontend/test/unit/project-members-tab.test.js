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
  ElInput: {
    name: 'ElInput',
    props: { modelValue: String, placeholder: String },
    emits: ['update:modelValue'],
    template: '<input :placeholder="placeholder" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
  ElMessage: { error: ui.error, success: ui.success, warning: vi.fn() },
  ElMessageBox: { confirm: ui.confirm },
  ElOption: { name: 'ElOption', template: '<option><slot /></option>' },
  ElSelect: { name: 'ElSelect', template: '<select><slot /></select>' },
  ElTable: { name: 'ElTable', props: { data: Array }, template: '<div><slot /></div>' },
  ElTableColumn: {
    name: 'ElTableColumn',
    template: '<div><slot name="header" /><slot :row="{ user_id: 7, role: \'reader\', user: { rd_username: \'alice\' } }" /></div>',
  },
  ElTag: { name: 'ElTag', template: '<span><slot /></span>' },
}));

import ProjectMembersTab from '@/pages/project/components/ProjectMembersTab.vue';

async function mountTab({ canManageMembers = false, canManageProjectAdmins = false } = {}) {
  const wrapper = mount(ProjectMembersTab, {
    props: { projectId: 1, canManageMembers, canManageProjectAdmins },
    global: {
      directives: { loading: () => undefined },
      stubs: {
        DataTable: {
          name: 'DataTable',
          props: ['data', 'loading', 'pagination'],
          emits: ['update:pagination'],
          template: '<section><slot /></section>',
        },
        QueryForm: { name: 'QueryForm', template: '<form><slot /></form>' },
      },
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
    const wrapper = await mountTab({ canManageMembers: true });

    await findButton(wrapper, '添加成员').trigger('click');
    await wrapper.find('.user-select').trigger('click');
    await findButton(wrapper, '保存').trigger('click');
    await flushPromises();

    expect(membershipApi.create).toHaveBeenCalledWith(1, { user_id: 2, role: 'reader' });
    expect(ui.error).toHaveBeenCalledWith('保存项目成员失败，请稍后重试');
  });

  it('shows the add-member form control only to project administrators and super administrators', async () => {
    const reader = await mountTab();

    expect(findButton(reader, '添加成员')).toBeUndefined();

    const projectAdmin = await mountTab({ canManageMembers: true });

    expect(findButton(projectAdmin, '添加成员')).toBeDefined();

    const wrapper = await mountTab({ canManageMembers: true, canManageProjectAdmins: true });

    expect(wrapper.find('.member-dialog').exists()).toBe(false);
    await findButton(wrapper, '添加成员').trigger('click');

    expect(wrapper.find('.member-dialog').exists()).toBe(true);
    expect(wrapper.findComponent({ name: 'ElDialog' }).props('appendToBody')).toBe(true);
  });

  it('creates a new project member with reader permission by default', async () => {
    membershipApi.create.mockResolvedValue({});
    const wrapper = await mountTab({ canManageMembers: true });

    await findButton(wrapper, '添加成员').trigger('click');
    await wrapper.find('.user-select').trigger('click');
    await findButton(wrapper, '保存').trigger('click');
    await flushPromises();

    expect(membershipApi.create).toHaveBeenCalledWith(1, { user_id: 2, role: 'reader' });
  });

  it('renders members when the API returns a paginated response', async () => {
    const members = [{ user_id: 9, role: 'editor', user: { rd_username: 'bob' } }];
    membershipApi.list.mockResolvedValue({ content: members });

    const wrapper = await mountTab();

    expect(wrapper.findComponent({ name: 'DataTable' }).props('data')).toEqual(members);
  });

  it('filters the loaded members by username without requesting a broader project membership list', async () => {
    const members = [
      { user_id: 9, role: 'editor', user: { rd_username: 'bob' } },
      { user_id: 10, role: 'reader', user: { rd_username: 'alice' } },
    ];
    membershipApi.list.mockResolvedValue(members);

    const wrapper = await mountTab();
    await wrapper.find('input[placeholder="按用户名筛选"]').setValue('bob');

    expect(wrapper.findComponent({ name: 'DataTable' }).props('data')).toEqual([members[0]]);
    expect(membershipApi.list).toHaveBeenCalledTimes(1);
    expect(membershipApi.list).toHaveBeenCalledWith(1);
  });

  it('paginates more than 20 filtered members so the table can scroll independently of the pager', async () => {
    const members = Array.from({ length: 21 }, (_, index) => ({
      user_id: index + 1,
      role: 'reader',
      user: { rd_username: `user-${index + 1}` },
    }));
    membershipApi.list.mockResolvedValue(members);

    const wrapper = await mountTab();
    const table = wrapper.getComponent({ name: 'DataTable' });

    expect(table.props('pagination')).toMatchObject({
      page: 1,
      pageSize: 20,
      total: 21,
      hideOnSinglePage: true,
      showJumper: true,
    });
    expect(table.props('data')).toEqual(members.slice(0, 20));

    table.vm.$emit('update:pagination', { page: 2, pageSize: 20 });
    await flushPromises();

    expect(table.props('data')).toEqual(members.slice(20));
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
