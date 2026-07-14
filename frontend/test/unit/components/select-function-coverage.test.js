import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

const accountApi = {
  fetch: vi.fn(() => Promise.resolve({
    result: {
      content: [
        { id: 11, commonName: 'Alice', emailAddress: 'alice@example.com', department: { name: 'RD' } },
      ],
    },
  })),
  fetchProfile: vi.fn((id) => Promise.resolve({
    result: {
      id,
      commonName: `User-${id}`,
      avatarUrl: '',
      department: { name: 'RD' },
    },
  })),
};

const domainGroupApi = {
  fetch: vi.fn(() => Promise.resolve({
    result: {
      content: [
        { id: 21, name: 'Team', emailAddress: 'team@example.com' },
      ],
    },
  })),
};

const projectApi = {
  fetch: vi.fn(() => Promise.resolve({
    content: [{ id: 31, name: 'Project-31' }],
  })),
  fetchById: vi.fn((id) => Promise.resolve({
    id,
    name: `Project-${id}`,
  })),
};

const groupTagApi = {
  fetch: vi.fn(() => Promise.resolve({ content: [] })),
  fetchById: vi.fn((id) => Promise.resolve({ id, name: `Tag-${id}` })),
};

const groupApi = {
  fetch: vi.fn(() => Promise.resolve({ content: [] })),
  fetchById: vi.fn((id) => Promise.resolve({ id, name: `Group-${id}` })),
};

vi.mock('@/api/account-api', () => ({ default: accountApi }));
vi.mock('@/api/domain-group-api', () => ({ default: domainGroupApi }));
vi.mock('@/api/project-api', () => ({ default: projectApi }));
vi.mock('@/api/group-tag-api', () => ({ default: groupTagApi }));
vi.mock('@/api/group-api', () => ({ default: groupApi }));
vi.mock('@/components/data/UserAvatar.vue', () => ({
  default: defineComponent({
    name: 'UserAvatar',
    setup() {
      return () => h('div');
    },
  }),
}));

const globalStubs = {
  ElSelect: defineComponent({
    name: 'ElSelect',
    props: {
      modelValue: {
        type: [String, Number, Array],
        default: null,
      },
      remoteMethod: {
        type: Function,
        default: undefined,
      },
      loading: Boolean,
      disabled: Boolean,
    },
    emits: ['update:modelValue'],
    setup(props, { emit, slots }) {
      return () => h('div', [
        slots.default?.(),
        h('button', {
          'data-test': 'update-model',
          onClick: () => emit('update:modelValue', props.modelValue),
        }),
      ]);
    },
  }),
  ElOption: defineComponent({
    name: 'ElOption',
    setup(_, { slots }) {
      return () => h('div', slots.default?.());
    },
  }),
  ElSpace: defineComponent({
    name: 'ElSpace',
    setup(_, { slots }) {
      return () => h('div', slots.default?.());
    },
  }),
};

describe('form select function coverage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('executes MailSelect search and update handlers', async () => {
    const { default: MailSelect } = await import('@/components/form/MailSelect.vue');
    const wrapper = shallowMount(MailSelect, {
      props: {
        modelValue: ['team@example.com'],
        multiple: true,
      },
      global: {
        stubs: globalStubs,
      },
    });

    const select = wrapper.findComponent({ name: 'ElSelect' });
    await select.props('remoteMethod')('team');
    await flushPromises();
    await select.vm.$emit('update:modelValue', ['alice@example.com', 'team@example.com']);

    expect(accountApi.fetch).toHaveBeenCalledWith({
      usernameOrRealNameOrNamePinyinLike: 'team',
    });
    expect(domainGroupApi.fetch).toHaveBeenCalledWith({
      nameLike: 'team',
      isEmailEnabled: true,
    });
    expect(wrapper.emitted('update:modelValue')).toEqual([
      [['alice@example.com', 'team@example.com']],
    ]);
  }, 15000);

  it('executes UserMail search and update handlers', async () => {
    const { default: UserMail } = await import('@/components/form/UserMail.vue');
    const wrapper = shallowMount(UserMail, {
      props: {
        modelValue: 'alice@example.com',
      },
      global: {
        stubs: globalStubs,
      },
    });

    const select = wrapper.findComponent({ name: 'ElSelect' });
    await select.props('remoteMethod')('alice');
    await flushPromises();
    await select.vm.$emit('update:modelValue', 'updated@example.com');

    expect(accountApi.fetch).toHaveBeenCalledWith({
      usernameOrRealNameOrNamePinyinLike: 'alice',
    });
    expect(wrapper.emitted('update:modelValue')).toEqual([
      ['updated@example.com'],
    ]);
  }, 15000);

  it('executes AccountSelect initialization, search and update handlers', async () => {
    const { default: AccountSelect } = await import('@/components/form/AccountSelect.vue');
    const wrapper = shallowMount(AccountSelect, {
      props: {
        modelValue: [7],
        multiple: true,
        type: 'public',
      },
      global: {
        stubs: globalStubs,
      },
    });

    const select = wrapper.findComponent({ name: 'ElSelect' });
    await flushPromises();
    await select.props('remoteMethod')('shared');
    await flushPromises();
    await select.vm.$emit('update:modelValue', [9, 10]);

    expect(accountApi.fetchProfile).toHaveBeenCalledWith(7);
    expect(accountApi.fetch).toHaveBeenCalledWith({
      usernameOrRealNameOrNamePinyinLike: 'shared',
      isPublicAccount: true,
    });
    expect(wrapper.emitted('update:modelValue')).toEqual([
      [[9, 10]],
    ]);
  }, 15000);

  it('executes ProjectSelect default loading, search and update handlers', async () => {
    const { default: ProjectSelect } = await import('@/components/form/ProjectSelect.vue');
    const wrapper = shallowMount(ProjectSelect, {
      props: {
        modelValue: null,
      },
      global: {
        stubs: globalStubs,
      },
    });

    const select = wrapper.findComponent({ name: 'ElSelect' });
    await flushPromises();
    await select.props('remoteMethod')('core');
    await flushPromises();
    await select.vm.$emit('update:modelValue', 31);

    expect(projectApi.fetch).toHaveBeenNthCalledWith(1, {
      page: 1,
      size: 20,
    });
    expect(projectApi.fetch).toHaveBeenNthCalledWith(2, {
      nameLike: 'core',
    });
    expect(wrapper.emitted('update:modelValue')).toEqual([
      [31],
    ]);
  }, 15000);

  it('executes ProjectSelect selected-value initialization branch', async () => {
    const { default: ProjectSelect } = await import('@/components/form/ProjectSelect.vue');

    shallowMount(ProjectSelect, {
      props: {
        modelValue: 99,
      },
      global: {
        stubs: globalStubs,
      },
    });

    await flushPromises();

    expect(projectApi.fetchById).toHaveBeenCalledWith(99);
  }, 15000);

  it('loads project group tag options', async () => {
    const { default: GroupTagSelect } = await import('@/components/form/GroupTagSelect.vue');
    const wrapper = shallowMount(GroupTagSelect, {
      props: {
        modelValue: null,
      },
      global: {
        stubs: globalStubs,
      },
    });

    await flushPromises();

    expect(groupTagApi.fetch).toHaveBeenCalledWith({
      page: 1,
      size: 20,
    });
    expect(wrapper.findAllComponents({ name: 'ElOption' })).toHaveLength(0);
    expect(wrapper.findComponent({ name: 'ElSelect' }).props('loading')).toBe(false);
  });

  it('scopes GroupSelect requests to the group tag and clears on scope change', async () => {
    const { default: GroupSelect } = await import('@/components/form/GroupSelect.vue');
    const wrapper = shallowMount(GroupSelect, {
      props: {
        modelValue: 9,
        projectId: 31,
        groupTagId: 7,
      },
      global: { stubs: globalStubs },
    });
    await flushPromises();

    expect(groupApi.fetchById).toHaveBeenCalledWith(9);
    await wrapper.setProps({ groupTagId: 8 });
    await flushPromises();

    expect(wrapper.emitted('update:modelValue')).toContainEqual([null]);
    expect(groupApi.fetch).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      project_id: 31,
      group_tag_id: 8,
    });

    const select = wrapper.findComponent({ name: 'ElSelect' });
    await select.props('remoteMethod')('ops');
    await flushPromises();
    select.vm.$emit('update:modelValue', 12);

    expect(groupApi.fetch).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      project_id: 31,
      group_tag_id: 8,
      nameLike: 'ops',
    });
    expect(wrapper.emitted('update:modelValue')).toContainEqual([12]);
  });
});
