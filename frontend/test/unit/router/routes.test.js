import { shallowMount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { vi } from 'vitest';
import App from '@/App.vue';
import RouteMenu from '@/layouts/components/RouteMenu.vue';
import { commonStubs } from '../../helpers/mount';

vi.mock('@/layouts/AppLayout.vue', () => ({
  default: {
    name: 'AppLayout',
    template: '<div><slot /></div>',
  },
}));

const { default: routes } = await import('@/router/routes');

describe('router/routes and app shell', () => {
  it('defines active public and admin routes', () => {
    const loginRoute = routes.find((route) => route.name === 'Login');
    const adminRoute = routes.find((route) => route.path === '/admin');
    const storageHealthRoute = routes
      .flatMap((route) => route.children || [])
      .find((route) => route.name === 'StorageHealth');
    const storageClusterDetailRoute = adminRoute.children
      .find((route) => route.name === 'StorageClusterDetail');
    const adminDashboardRoute = adminRoute.children
      .find((route) => route.name === 'AdminDashboard');

    expect(loginRoute.meta.isPublic).toBe(true);
    expect(storageHealthRoute).toBeUndefined();
    expect(adminDashboardRoute).toBeUndefined();
    expect(storageClusterDetailRoute).toEqual(expect.objectContaining({
      path: 'storage-cluster/:id',
      meta: expect.objectContaining({
        title: '存储集群详情',
        isHidden: true,
        breadcrumb: ['系统管理', '存储集群', '存储集群详情'],
      }),
    }));
    expect(adminRoute.children.map((route) => route.name)).toEqual(
      expect.arrayContaining([
        'StorageClusters',
        'GroupTags',
        'Aggregates',
        'Volumes',
        'Qtrees',
        'UsersManagement',
        'BackUp',
        'Settings',
        'AICenter',
        'AIAuditDetail',
      ]),
    );

    const groupTagRoute = adminRoute.children.find(
      (route) => route.name === 'GroupTags',
    );
    expect(groupTagRoute).toEqual(expect.objectContaining({
      path: 'group-tags',
      meta: expect.objectContaining({ title: '项目组标签' }),
    }));

    expect(Object.fromEntries(
      adminRoute.children
        .filter((route) => [
          'Aggregates', 'AggregateDetail', 'Volumes', 'VolumeDetail', 'Qtrees', 'QtreeDetail',
        ].includes(route.name))
        .map((route) => [route.name, route.meta.title]),
    )).toEqual({
      Aggregates: '容量池',
      AggregateDetail: '容量池详情',
      Volumes: '存储空间',
      VolumeDetail: '存储空间详情',
      Qtrees: 'Qtree（NetApp）',
      QtreeDetail: 'Qtree（NetApp）详情',
    });
  });

  it('uses consistent DiskPulse domain titles in visible navigation', () => {
    const rootTitles = routes
      .flatMap((route) => route.children ?? [route])
      .filter((route) => route.meta?.isRoot)
      .map((route) => route.meta.title);
    const adminRoute = routes.find((route) => route.path === '/admin');
    const adminTitles = adminRoute.children
      .filter((route) => !route.meta?.isHidden)
      .map((route) => route.meta.title);

    expect(rootTitles).toEqual(expect.arrayContaining(['概览', '用户目录', '项目', '项目组', '告警']));
    expect(adminTitles).toEqual(expect.arrayContaining([
      '项目组标签',
      '存储集群',
      '容量池',
      '存储空间',
      'Qtree（NetApp）',
      '用户信息管理',
      '系统设置',
      'AI 中心',
    ]));
    expect([...rootTitles, ...adminTitles]).not.toEqual(expect.arrayContaining(['用户', 'Volume', 'Qtree']));
  });

  it('declares complete breadcrumb hierarchies for every detail route', () => {
    const adminRoute = routes.find((route) => route.path === '/admin');
    const detailBreadcrumbs = [
      ...routes.flatMap((route) => route.children || []),
      ...adminRoute.children,
    ]
      .filter((route) => route.meta?.isHidden && route.name?.endsWith('Detail'))
      .map((route) => [route.name, route.meta.breadcrumb]);

    expect(Object.fromEntries(detailBreadcrumbs)).toEqual({
      UsagesDetail: ['用户目录', '使用详情'],
      ProjectDetail: ['项目', '项目详情'],
      GroupDetail: ['项目组', '项目组详情'],
      StorageClusterDetail: ['系统管理', '存储集群', '存储集群详情'],
      AggregateDetail: ['系统管理', '容量池', '容量池详情'],
      VolumeDetail: ['系统管理', '存储空间', '存储空间详情'],
      QtreeDetail: ['系统管理', 'Qtree（NetApp）', 'Qtree（NetApp）详情'],
      AIAuditDetail: ['系统管理', 'AI 中心', 'AI 审计详情'],
      AuditEventDetail: ['系统管理', '统一操作审计', '审计事件详情'],
    });
  });

  it('mounts the root app shell', () => {
    const wrapper = shallowMount(App, {
      global: {
        stubs: commonStubs,
      },
    });

    expect(wrapper.exists()).toBe(true);
    expect(wrapper.findComponent({ name: 'ElConfigProvider' }).exists()).toBe(true);
  });

  it('places AI assistant immediately after project groups', () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes,
    });
    const wrapper = shallowMount(RouteMenu, {
      global: {
        plugins: [createPinia(), router],
        stubs: {
          ElMenu: { template: '<div><slot /></div>' },
          RouteMenuItem: {
            props: ['option'],
            template: '<span class="menu-item">{{ option.label }}</span>',
          },
        },
      },
    });
    const labels = wrapper.findAll('.menu-item').map((item) => item.text());

    expect(labels[labels.indexOf('项目组') + 1]).toBe('AI 助手');
  });

  it('orders system management from storage resources to platform administration with semantic icons', () => {
    const adminRoute = routes.find((route) => route.path === '/admin');
    const visibleRoutes = adminRoute.children.filter((route) => !route.meta?.isHidden);

    expect(visibleRoutes.map((route) => route.name)).toEqual([
      'StorageClusters',
      'Aggregates',
      'Volumes',
      'Qtrees',
      'GroupTags',
      'UsersManagement',
      'Settings',
      'AICenter',
      'AuditEvents',
    ]);
    expect(Object.fromEntries(visibleRoutes.map((route) => [route.name, route.meta.icon]))).toEqual({
      StorageClusters: 'i-ri-server-line',
      Aggregates: 'i-ri-pie-chart-2-line',
      Volumes: 'i-ri-database-2-line',
      Qtrees: 'i-ri-folder-2-line',
      GroupTags: 'i-ri-price-tag-3-line',
      UsersManagement: 'i-ri-team-line',
      Settings: 'i-ri-settings-3-line',
      AICenter: 'i-ri-robot-2-line',
      AuditEvents: 'i-ri-file-search-line',
    });
  });
});
