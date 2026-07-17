import { shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';
import { commonStubs } from '../../helpers/mount';

vi.mock('element-plus', () => ({
  ElLink: commonStubs.ElLink,
  ElAvatar: commonStubs.ElAvatar,
  ElButton: commonStubs.ElButton,
  ElCard: commonStubs.ElCard,
  ElPagination: commonStubs.ElPagination,
  ElRow: commonStubs.ElCard,
  ElCol: commonStubs.ElCard,
  ElTable: commonStubs.ElTable,
  ElTableColumn: commonStubs.ElCard,
  ElForm: commonStubs.ElForm,
  ElConfigProvider: commonStubs.ElConfigProvider,
  ElDescriptions: commonStubs.ElDescriptions,
  ElDescriptionsItem: commonStubs.ElDescriptionsItem,
  ElEmpty: commonStubs.ElCard,
  ElMessage: { error: vi.fn() },
  ElTabPane: commonStubs.ElCard,
  ElTabs: commonStubs.ElCard,
  ElTag: commonStubs.ElCard,
}));

vi.mock('@/stores/app-settings', () => ({
  useAppSettings: () => ({
    theme: 'light',
    toggleTheme: vi.fn(() => true),
  }),
}));

vi.mock('@/stores/breadcrumbs', () => ({
  useBreadcrumbs: () => ({
    detailTitleFor: vi.fn(() => ''),
    setDetailTitle: vi.fn(),
  }),
}));

vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router');

  return {
    ...actual,
    useRoute: () => ({
      params: {
        id: '12',
      },
      query: {},
    }),
    useRouter: () => ({ replace: vi.fn(() => Promise.resolve()) }),
  };
});

vi.mock('@/api/group-api.js', () => ({
  default: {
    fetch: vi.fn(() => Promise.resolve({ content: [], total: 0 })),
  },
}));

vi.mock('@/api/project-api.js', () => ({
  default: {
    fetchById: vi.fn(() => Promise.resolve(null)),
  },
}));

vi.mock('@/pages/common/RealTimePage.vue', () => ({
  default: {
    name: 'RealTimePage',
    props: ['attributeId', 'apiType', 'label'],
    template: '<div class="real-time-page-stub"><slot name="extra-descriptions" :info="{ project: { name: \'A\' }, qtree: { name: \'Q\' } }" /></div>',
  },
}));

describe('lightweight component and page smoke tests', () => {
  it('mounts reusable basic and data components', async () => {
    const { default: AppLink } = await import('@/components/basic/AppLink.vue');
    const { default: GridContainer } = await import('@/components/basic/GridContainer.vue');
    const { default: ThemeSwitch } = await import('@/components/basic/ThemeSwitch.vue');
    const { default: Result } = await import('@/components/data/Result.vue');
    const { default: UserAvatar } = await import('@/components/data/UserAvatar.vue');
    const { default: DataTable } = await import('@/components/data/DataTable.vue');
    const { default: QueryForm } = await import('@/components/form/QueryForm.vue');

    expect(shallowMount(AppLink, {
      props: { to: '/projects' },
      slots: { default: 'Projects' },
      global: { stubs: commonStubs },
    }).text()).toContain('Projects');

    expect(shallowMount(GridContainer, {
      slots: { default: '<div>Body</div>', tail: '<div>Tail</div>' },
    }).text()).toContain('Tail');

    const themeWrapper = shallowMount(ThemeSwitch, {
      global: { stubs: commonStubs },
    });
    await themeWrapper.find('button').trigger('click');

    expect(shallowMount(Result, {
      props: { type: '404', title: 'Not Found', tip: 'Missing' },
      global: { stubs: commonStubs },
    }).text()).toContain('Not Found');

    expect(shallowMount(UserAvatar, {
      props: { src: 'avatar.png' },
      global: { stubs: commonStubs },
    }).exists()).toBe(true);

    const dataTable = shallowMount(DataTable, {
      props: {
        data: [{ id: 1 }],
        pagination: {
          page: 1,
          pageSize: 20,
          total: 1,
          pageSizes: [20],
          showJumper: true,
        },
      },
      global: {
        stubs: commonStubs,
        directives: {
          loading: () => undefined,
        },
      },
    });
    dataTable.vm.$emit('update:pagination', { page: 2 });
    expect(dataTable.exists()).toBe(true);

    const queryForm = shallowMount(QueryForm, {
      slots: {
        default: '<div>Filters</div>',
        actions: '<div>Actions</div>',
        advanced: '<div>Advanced</div>',
        exportExcel: '<div>Export</div>',
      },
      global: {
        stubs: {
          ...commonStubs,
          GridContainer: {
            template: '<div><slot /><div><slot name="tail" /></div></div>',
          },
        },
      },
    });
    expect(queryForm.text()).toContain('Filters');
    expect(queryForm.text()).toContain('Actions');
  });

  it('mounts active error pages and detail wrappers', async () => {
    const { default: NotFoundPage } = await import('@/pages/error/NotFoundPage.vue');
    const { default: UnauthorizedPage } = await import('@/pages/error/UnauthorizedPage.vue');
    const { default: ProjectDetailPage } = await import('@/pages/project/ProjectDetailPage.vue');
    const { default: GroupDetailPage } = await import('@/pages/group/GroupDetailPage.vue');
    const { default: UsageDetailPage } = await import('@/pages/usage/UsageDetailPage.vue');
    const { default: AggregateDetailPage } = await import('@/pages/admin/aggregate/AggregateDetailPage.vue');
    const { default: QtreeDetailPage } = await import('@/pages/admin/qtree/QtreeDetailPage.vue');
    const { default: VolumeDetailPage } = await import('@/pages/admin/volume/VolumeDetailPage.vue');

    [
      NotFoundPage,
      UnauthorizedPage,
      ProjectDetailPage,
      GroupDetailPage,
      UsageDetailPage,
      AggregateDetailPage,
      QtreeDetailPage,
      VolumeDetailPage,
    ].forEach((component) => {
      expect(shallowMount(component, {
        global: {
          stubs: {
            ...commonStubs,
            ProjectMembersTab: true,
            ProjectAuditTab: true,
            StorageTypeTag: true,
          },
        },
      }).exists()).toBe(true);
    });
  });
});
