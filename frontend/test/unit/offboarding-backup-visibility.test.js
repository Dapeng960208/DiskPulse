import { mount, shallowMount } from '@vue/test-utils';
import { defineComponent, h, ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';

const configApi = vi.hoisted(() => ({
  fetch: vi.fn(() => Promise.resolve({ back_up_enabled: true })),
  updateConfig: vi.fn(),
}));

vi.mock('@/api/config-api', () => ({ default: configApi }));
vi.mock('@/router', () => ({ default: { push: vi.fn() } }));
vi.mock('@/layouts/AppLayout.vue', () => ({ default: { template: '<div />' } }));
vi.mock('@/pages/common/RealTimePage.vue', () => ({
  default: defineComponent({
    name: 'RealTimePage',
    setup(_, { slots }) {
      return () => h('div', (slots.extraDescriptions ?? slots['extra-descriptions'])?.({
        info: { back_path: '/backup' },
      }));
    },
  }),
}));
vi.mock('vue-router', async () => ({
  ...(await vi.importActual('vue-router')),
  useRoute: () => ({ params: { id: '1' } }),
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock('@/stores/current-user', () => ({
  useCurrentUser: () => ({ extensionAttributes: {} }),
}));
vi.mock('@/utils/authorization', () => ({ hasRole: () => true }));
vi.mock('@/composables/query', () => ({
  useQuery: (_request, initialValue) => ({
    result: ref(initialValue),
    querying: ref(false),
    query: vi.fn(),
  }),
  useQueryParams: (provider) => ({
    queryParams: ref(provider()),
    reset: vi.fn(),
  }),
}));

const mountOptions = {
  global: {
    renderStubDefaultSlot: true,
    stubs: {
      ElTableColumn: defineComponent({
        name: 'ElTableColumn',
        props: ['label'],
        setup(_, { slots }) {
          const row = { user: {}, storage_target: {} };
          return () => h('div', slots.default ? slots.default({ row }) : []);
        },
      }),
    },
  },
};
const DescriptionsItemStub = defineComponent({
  name: 'ElDescriptionsItem',
  props: ['label'],
  setup(_, { slots }) {
    return () => h('div', slots.default?.());
  },
});

describe('offboarding backup visibility', () => {
  it('keeps the backup route registered but hides it from navigation', async () => {
    const { default: routes } = await import('@/router/routes');
    const adminRoute = routes.find((route) => route.path === '/admin');
    const backupRoute = adminRoute.children.find((route) => route.name === 'BackUp');

    expect(backupRoute).toBeTruthy();
    expect(backupRoute.meta.isHidden).toBe(true);
  });

  it('does not render backup settings', async () => {
    const { default: SettingsPage } = await import('@/pages/admin/settings/SettingsPage.vue');
    const wrapper = shallowMount(SettingsPage, mountOptions);
    const labels = wrapper.findAllComponents({ name: 'ElTabPane' }).map((tab) => tab.props('label'));

    expect(labels).not.toContain('目录操作和备份配置');
  });

  it('does not render the backup column on the group list', async () => {
    const { default: GroupListPage } = await import('@/pages/group/GroupListPage.vue');
    const groupList = shallowMount(GroupListPage, mountOptions);

    expect(groupList.findAllComponents({ name: 'ElTableColumn' }).map((column) => column.props('label')))
      .not.toContain('开启离职备份');
  }, 15000);

  it('does not render the backup setting in the group form', async () => {
    const { default: GroupFormDialog } = await import('@/pages/group/components/GroupFormDialog.vue');
    const groupForm = shallowMount(GroupFormDialog, mountOptions);

    expect(groupForm.findAllComponents({ name: 'ElFormItem' }).map((item) => item.props('label')))
      .not.toContain('是否开启离职数据备份');
  }, 15000);

  it('does not render the backup path on the group detail', async () => {
    const { default: GroupDetailPage } = await import('@/pages/group/GroupDetailPage.vue');
    const groupDetail = mount(GroupDetailPage, {
      global: { stubs: { ElDescriptionsItem: DescriptionsItemStub } },
    });

    expect(groupDetail.findAllComponents({ name: 'ElDescriptionsItem' }).map((item) => item.props('label')))
      .not.toContain('备份路径');
  });

  it('does not render the move-to-backup action on usage rows', async () => {
    const { default: UsageListPage } = await import('@/pages/usage/UsageListPage.vue');
    const usageList = shallowMount(UsageListPage, mountOptions);

    expect(usageList.text()).not.toContain('移至备份');
  }, 15000);
});
