import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const loginMock = vi.fn();
const fetchProfileMock = vi.fn();
const setTokenMock = vi.fn();
const pushMock = vi.fn();

vi.mock('@/api/users-api', () => ({
  default: {
    login: loginMock,
    fetchProfile: fetchProfileMock,
  },
}));

vi.mock('@/utils/authorization', () => ({
  setToken: setTokenMock,
}));

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
  useRoute: () => ({ query: {} }),
}));

vi.mock('element-plus', async () => {
  const { defineComponent, h } = await import('vue');

  return {
    ElMessage: { success: vi.fn() },
    ElForm: defineComponent({
      name: 'ElForm',
      methods: {
        validate: vi.fn().mockResolvedValue(true),
      },
      setup(_, { slots }) {
        return () => h('form', slots.default ? slots.default() : []);
      },
    }),
    ElFormItem: defineComponent({
      name: 'ElFormItem',
      setup(_, { slots }) {
        return () => h('div', slots.default ? slots.default() : []);
      },
    }),
    ElInput: defineComponent({
      name: 'ElInput',
      inheritAttrs: false,
      props: ['modelValue'],
      emits: ['update:modelValue'],
      setup(props, { emit }) {
        return () => h('input', {
          value: props.modelValue,
          onInput: (event) => emit('update:modelValue', event.target.value),
        });
      },
    }),
    ElAlert: defineComponent({
      name: 'ElAlert',
      setup() {
        return () => h('div');
      },
    }),
    ElButton: defineComponent({
      name: 'ElButton',
      emits: ['click'],
      setup(_, { emit, slots }) {
        return () => h('button', { type: 'button', onClick: () => emit('click') }, slots.default ? slots.default() : []);
      },
    }),
  };
});

vi.mock('@element-plus/icons-vue', () => ({
  User: {},
  Lock: {},
}));

vi.mock('@/components/basic/ThemeSwitch.vue', () => ({
  default: { template: '<div />' },
}));

describe('LoginPage LDAP flow', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    loginMock.mockReset();
    fetchProfileMock.mockReset();
    setTokenMock.mockReset();
    pushMock.mockReset();
  });

  it('sends superadmin through backend login instead of local bypass', async () => {
    loginMock.mockResolvedValue({ result: { token: 'jwt-token' } });
    fetchProfileMock.mockResolvedValue({
      result: {
        id: 1,
        avatarUrl: '',
        commonName: 'Root Admin',
        roleCodes: ['superadmin'],
        permissionCodes: [['*', '*', '*']],
        extensionAttributes: { rdUsername: 'superadmin' },
      },
    });

    const { default: LoginPage } = await import('@/pages/auth/LoginPage.vue');
    const wrapper = mount(LoginPage, {
      global: {
        stubs: {
          ThemeSwitch: { template: '<div />' },
        },
      },
    });

    const inputs = wrapper.findAll('input');
    await inputs[0].setValue('superadmin');
    await inputs[1].setValue('secret-password');
    await wrapper.find('button').trigger('click');
    await flushPromises();

    expect(loginMock).toHaveBeenCalledWith('superadmin', 'secret-password');
    expect(setTokenMock).toHaveBeenCalledWith('jwt-token');
    expect(fetchProfileMock).toHaveBeenCalled();
    expect(pushMock).toHaveBeenCalledWith('/');
  });
});
