import { defineComponent, h, nextTick } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

const { confirmMock, successMock, hasRoleMock } = vi.hoisted(() => ({
  confirmMock: vi.fn(() => Promise.resolve()),
  successMock: vi.fn(),
  hasRoleMock: vi.fn(() => true),
}));

vi.mock('element-plus', async (importOriginal) => ({
  ...(await importOriginal()),
  ElMessageBox: { confirm: confirmMock },
  ElMessage: { success: successMock },
}));

vi.mock('vue-router', async () => ({
  ...(await vi.importActual('vue-router')),
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('@/utils/authorization', () => ({
  hasRole: hasRoleMock,
}));

const { default: usersApi } = await import('@/api/users-api');
const { default: routes } = await import('@/router/routes');
const { default: UserListPage } = await import('@/pages/admin/user/UserListPage.vue');
const { default: UserFormDialog } = await import('@/pages/admin/user/components/UserFormDialog.vue');

const passthrough = (name, props = {}) => defineComponent({
  name,
  props,
  setup(_, { slots }) {
    return () => h('div', slots.default?.());
  },
});

const ButtonStub = defineComponent({
  name: 'ElButton',
  props: {
    disabled: Boolean,
    loading: Boolean,
  },
  emits: ['click'],
  setup(props, { emit, slots }) {
    return () => h('button', {
      disabled: props.disabled || props.loading,
      onClick: () => emit('click'),
    }, slots.default?.());
  },
});

const FormItemStub = passthrough('ElFormItem', { label: String, prop: String });
const TableColumnStub = defineComponent({
  name: 'ElTableColumn',
  props: { label: String, prop: String },
  setup(_, { slots }) {
    return () => h('div', [
      slots.header?.(),
      slots.default?.({
        row: {
          id: 1,
          rd_username: 'alice',
          username: 'Alice',
          email: 'alice@example.com',
          department: '研发部',
          user_type: 2,
          is_alert: true,
          storage_used: 1,
        },
      }),
    ]);
  },
});
const InputStub = defineComponent({
  name: 'ElInput',
  props: {
    modelValue: String,
    disabled: Boolean,
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('input', {
      disabled: props.disabled,
      value: props.modelValue,
      onInput: (event) => emit('update:modelValue', event.target.value),
    });
  },
});

const dialogEditMock = vi.fn();
const UserFormDialogStub = defineComponent({
  name: 'UserFormDialog',
  setup(_, { expose }) {
    expose({ edit: dialogEditMock });
    return () => h('div');
  },
});

const pageStubs = {
  FilterForm: passthrough('FilterForm'),
  DataTable: passthrough('DataTable', { pagination: Object, loading: Boolean, data: Array }),
  ElButton: ButtonStub,
  ElCard: passthrough('ElCard'),
  ElDivider: passthrough('ElDivider'),
  ElFormItem: FormItemStub,
  ElInput: InputStub,
  ElOption: defineComponent({ name: 'ElOption', template: '<option />' }),
  ElSelect: passthrough('ElSelect'),
  ElTableColumn: TableColumnStub,
  ElTag: passthrough('ElTag'),
  UserAvatar: defineComponent({ name: 'UserAvatar', template: '<div />' }),
  UserFormDialog: UserFormDialogStub,
};

function findButton(wrapper, text) {
  return wrapper.findAll('button').find((button) => button.text().includes(text));
}

function findFormItem(wrapper, label) {
  return wrapper.findAllComponents({ name: 'ElFormItem' })
    .find((item) => item.props('label') === label);
}

describe('user management LDAP sync contracts', () => {
  it('posts LDAP synchronization to /users/sync-ldap', async () => {
    const postSpy = vi.spyOn(usersApi.request, 'post').mockResolvedValue({ data: {} });

    try {
      expect(usersApi.syncLdap).toBeTypeOf('function');
      await usersApi.syncLdap();
      expect(postSpy.mock.calls.at(-1)?.[0]).toBe('/users/sync-ldap');
    } finally {
      postSpy.mockRestore();
    }
  });

  it('names /admin/users 用户信息管理 and restricts it to superadmin', () => {
    const adminRoute = routes.find((route) => route.path === '/admin');
    const usersRoute = adminRoute.children.find((route) => route.path === 'users');

    expect(usersRoute.meta.title).toBe('用户信息管理');
    expect(usersRoute.meta.isAccessible()).toBe(200);
    expect(hasRoleMock).toHaveBeenCalledWith('superadmin');

    hasRoleMock.mockReturnValueOnce(false);
    expect(usersRoute.meta.isAccessible()).toBe(403);
  });

  describe('user management page', () => {
    let fetchSpy;
    let syncLdapMock;

    beforeEach(() => {
      fetchSpy = vi.spyOn(usersApi, 'fetch').mockResolvedValue({ content: [], total: 0 });
      syncLdapMock = vi.fn(() => Promise.resolve({
        ldap_total: 6,
        created: 2,
        updated: 3,
        reactivated: 1,
        marked_inactive: 4,
      }));
      usersApi.syncLdap = syncLdapMock;
      dialogEditMock.mockClear();
    });

    afterEach(() => {
      fetchSpy.mockRestore();
    });

    async function mountPage() {
      const wrapper = shallowMount(UserListPage, { global: { stubs: pageStubs } });
      await flushPromises();
      return wrapper;
    }

    it('exposes add and LDAP sync actions with the complete safety confirmation', async () => {
      const wrapper = await mountPage();
      const addButton = findButton(wrapper, '新增用户');
      const syncButton = findButton(wrapper, '同步LDAP');

      expect(addButton).toBeTruthy();
      expect(syncButton).toBeTruthy();

      await addButton.trigger('click');
      expect(dialogEditMock).toHaveBeenCalledWith();

      await syncButton.trigger('click');
      await flushPromises();

      const confirmation = confirmMock.mock.calls.at(-1)?.[0];
      expect(confirmation).toContain('缺失的在职用户会转为离职');
      expect(confirmation).toContain('离职用户重新出现会恢复在职');
      expect(confirmation).toContain('公共用户类型不会自动改变');
      expect(confirmation).toContain('不会删除任何用户');
    });

    it('blocks repeat synchronization, reports counts, and refreshes page 1', async () => {
      let resolveSync;
      syncLdapMock.mockImplementationOnce(() => new Promise((resolve) => {
        resolveSync = resolve;
      }));
      const wrapper = await mountPage();
      await wrapper.findComponent({ name: 'DataTable' }).vm.$emit('update:pagination', {
        page: 3,
        pageSize: 20,
      });
      await flushPromises();

      const syncButton = findButton(wrapper, '同步LDAP');
      expect(syncButton).toBeTruthy();
      await syncButton.trigger('click');
      await flushPromises();

      expect(syncButton.attributes('disabled')).toBeDefined();
      await syncButton.trigger('click');
      expect(syncLdapMock).toHaveBeenCalledTimes(1);

      resolveSync({
        ldap_total: 6,
        created: 2,
        updated: 3,
        reactivated: 1,
        marked_inactive: 4,
      });
      await flushPromises();

      expect(successMock).toHaveBeenCalledWith(expect.stringMatching(
        /LDAP.*6.*新增.*2.*更新.*3.*恢复.*1.*离职.*4/,
      ));
      expect(fetchSpy).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1 }));
    });

    it('shows the complete user information columns', async () => {
      const wrapper = await mountPage();
      const labels = wrapper.findAllComponents({ name: 'ElTableColumn' })
        .map((column) => column.props('label'));

      expect(labels).toEqual(expect.arrayContaining([
        '用户名',
        '姓名',
        '邮箱',
        '部门',
        '账户类型',
        '告警状态',
        '存储用量',
      ]));
    });
  });

  it('allows administrators to maintain user fields while locking usernames on edit', async () => {
    const wrapper = shallowMount(UserFormDialog, {
      global: {
        stubs: {
          ElButton: ButtonStub,
          ElDialog: passthrough('ElDialog'),
          ElForm: passthrough('ElForm'),
          ElFormItem: FormItemStub,
          ElInput: InputStub,
          ElOption: defineComponent({ name: 'ElOption', template: '<option />' }),
          ElSelect: passthrough('ElSelect', { disabled: Boolean }),
          ElSwitch: defineComponent({
            name: 'ElSwitch',
            props: { disabled: Boolean, modelValue: Boolean },
            template: '<input type="checkbox" :disabled="disabled" />',
          }),
        },
      },
    });

    const expectedFields = ['用户名', '姓名', '邮箱', '部门', '账户类型', '告警状态'];
    const labels = wrapper.findAllComponents({ name: 'ElFormItem' })
      .map((item) => item.props('label'));
    expect(labels).toEqual(expect.arrayContaining(expectedFields));

    const createUsername = findFormItem(wrapper, '用户名').findComponent({ name: 'ElInput' });
    expect(createUsername.props('disabled')).toBe(false);

    wrapper.vm.$.exposed.edit({
      id: 9,
      rd_username: 'alice',
      username: 'Alice',
      email: 'alice@example.com',
      department: '研发部',
      user_type: 2,
      is_alert: true,
    });
    await nextTick();

    expect(findFormItem(wrapper, '用户名').findComponent({ name: 'ElInput' }).props('disabled')).toBe(true);
    for (const label of ['姓名', '邮箱', '部门']) {
      expect(findFormItem(wrapper, label).findComponent({ name: 'ElInput' }).props('disabled')).toBe(false);
    }
    expect(findFormItem(wrapper, '账户类型').findComponent({ name: 'ElSelect' }).props('disabled')).toBe(false);
    expect(findFormItem(wrapper, '告警状态').findComponent({ name: 'ElSwitch' }).props('disabled')).toBe(false);
  });
});
