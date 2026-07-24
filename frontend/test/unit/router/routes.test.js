import { shallowMount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { vi } from 'vitest';
import App from '@/App.vue';
import RouteMenu from '@/layouts/components/RouteMenu.vue';
import RouteMenuItem from '@/layouts/components/RouteMenuItem.vue';
import { commonStubs } from '../../helpers/mount';

const hasRole = vi.hoisted(() => vi.fn(() => true));

vi.mock('@/utils/authorization', () => ({ hasRole }));

vi.mock('@/layouts/AppLayout.vue', () => ({
  default: {
    name: 'AppLayout',
    template: '<div><slot /></div>',
  },
}));

const { default: routes } = await import('@/router/routes');

describe('router/routes and app shell', () => {
  it('uses one root layout route for every workspace route', () => {
    const rootLayoutRoutes = routes.filter(
      (route) => route.path === '/' && route.component?.name === 'AppLayout',
    );

    expect(rootLayoutRoutes).toHaveLength(1);
    expect(rootLayoutRoutes[0].children.map((route) => route.name)).toEqual(
      expect.arrayContaining([
        'Dashboard',
        'Usages',
        'UsagesDetail',
        'UsageCapacityPrediction',
        'CapacityPredictions',
        'Projects',
        'ProjectDetail',
        'Groups',
        'GroupDetail',
        'GroupCapacityPrediction',
        'Alerts',
        'AIChat',
      ]),
    );
  });

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
    const adminResourceRoutes = adminRoute.children.flatMap((route) => route.children || [route]);
    expect(adminResourceRoutes.map((route) => route.name)).toEqual(
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
        'ForecastGovernance',
        'VendorEventDefinitions',
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
      adminResourceRoutes
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

    expect(rootTitles).toEqual(expect.arrayContaining(['概览', '项目', 'AI 助手', '告警']));
    expect(rootTitles).not.toContain('容量预测');
    expect(rootTitles).not.toEqual(expect.arrayContaining(['用户目录', '项目组']));
    expect(adminTitles).toEqual(expect.arrayContaining([
      '项目组标签',
      '存储集群',
      '用户信息管理',
      '系统设置',
      'AI 中心',
      '容量预测治理',
    ]));
    expect([...rootTitles, ...adminTitles]).not.toEqual(expect.arrayContaining(['用户', 'Volume', 'Qtree']));
  });

  it('places Incident Center under System Management for super administrators only', () => {
    const adminRoute = routes.find((route) => route.path === '/admin');
    const rootIncidentRoute = routes
      .filter((route) => route.path !== '/admin')
      .flatMap((route) => route.children || [])
      .find((route) => route.name === 'IncidentCenter');
    const incidentRoute = adminRoute.children.find((route) => route.name === 'IncidentCenter');

    expect(rootIncidentRoute).toBeUndefined();
    expect(incidentRoute).toEqual(expect.objectContaining({
      path: 'incidents',
      meta: expect.objectContaining({
        title: '事件中心',
        icon: 'i-ri-alarm-warning-line',
      }),
    }));

    hasRole.mockReturnValueOnce(false).mockReturnValueOnce(true);
    expect(incidentRoute.meta.isAccessible()).toBe(403);
    expect(incidentRoute.meta.isAccessible()).toBe(200);
    expect(hasRole).toHaveBeenLastCalledWith('superadmin');
  });

  it('places vendor event associations under System Management for super administrators only', () => {
    const adminRoute = routes.find((route) => route.path === '/admin');
    const associationRoute = adminRoute.children
      .find((route) => route.name === 'VendorEventDefinitions');

    expect(associationRoute).toEqual(expect.objectContaining({
      path: 'vendor-event-definitions',
      meta: expect.objectContaining({
        title: '厂商事件关联目录',
        icon: 'i-ri-links-line',
      }),
    }));

    hasRole.mockReturnValueOnce(false).mockReturnValueOnce(true);
    expect(associationRoute.meta.isAccessible()).toBe(403);
    expect(associationRoute.meta.isAccessible()).toBe(200);
    expect(hasRole).toHaveBeenLastCalledWith('superadmin');
  });

  it('evaluates every declared route access policy', () => {
    const visit = (items) => items.flatMap((route) => [
      ...(route.meta?.isAccessible ? [route.meta.isAccessible] : []),
      ...visit(route.children || []),
    ]);
    const accessPolicies = visit(routes);

    expect(accessPolicies.length).toBeGreaterThan(1);
    expect(accessPolicies.map((policy) => policy())).toEqual(
      expect.arrayContaining([200]),
    );
    expect(hasRole).toHaveBeenCalled();
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

  it('does not expose capacity prediction as a standalone menu entry', () => {
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

    expect(labels).not.toContain('容量预测');
    expect(labels).not.toContain('项目组');
    expect(labels).not.toContain('用户目录');
  });

  it('keeps storage clusters as the direct menu entry and hides standalone inventory routes', () => {
    const adminRoute = routes.find((route) => route.path === '/admin');
    const storageRoute = adminRoute.children.find((route) => route.name === 'StorageClusters');
    const visibleRoutes = adminRoute.children.filter((route) => !route.meta?.isHidden);

    expect(storageRoute).toEqual(expect.objectContaining({
      path: 'storage-clusters',
      meta: expect.objectContaining({ title: '存储集群', icon: 'i-ri-server-line' }),
    }));
    expect(storageRoute.children).toBeUndefined();
    expect(adminRoute.children
      .filter((route) => ['Aggregates', 'Volumes', 'Qtrees'].includes(route.name))
      .every((route) => route.meta.isHidden)).toBe(true);
    expect(visibleRoutes.map((route) => route.name)).toEqual([
      'StorageClusters',
      'GroupTags',
      'UsersManagement',
      'Settings',
      'AICenter',
      'ForecastGovernance',
      'IncidentCenter',
      'VendorEventDefinitions',
      'AuditEvents',
    ]);
    expect(Object.fromEntries(visibleRoutes.filter((route) => route.name).map((route) => [route.name, route.meta.icon]))).toEqual({
      StorageClusters: 'i-ri-server-line',
      GroupTags: 'i-ri-price-tag-3-line',
      UsersManagement: 'i-ri-team-line',
      Settings: 'i-ri-settings-3-line',
      AICenter: 'i-ri-robot-2-line',
      ForecastGovernance: 'i-ri-line-chart-line',
      VendorEventDefinitions: 'i-ri-links-line',
      IncidentCenter: 'i-ri-alarm-warning-line',
      AuditEvents: 'i-ri-file-search-line',
    });

    const router = createRouter({ history: createMemoryHistory(), routes });
    expect(Object.fromEntries(['StorageClusters', 'Aggregates', 'Volumes', 'Qtrees'].map((name) => [
      name,
      router.resolve({ name }).path,
    ]))).toEqual({
      StorageClusters: '/admin/storage-clusters',
      Aggregates: '/admin/aggregates',
      Volumes: '/admin/volumes',
      Qtrees: '/admin/qtrees',
    });
  });

  it('classifies System Management entries after the standalone storage cluster entry', () => {
    const router = createRouter({ history: createMemoryHistory(), routes });
    const wrapper = shallowMount(RouteMenu, {
      global: {
        plugins: [createPinia(), router],
        stubs: {
          ElMenu: { template: '<div><slot /></div>' },
          RouteMenuItem: {
            name: 'RouteMenuItem',
            props: ['option'],
            template: '<span class="menu-item">{{ option.label }}</span>',
          },
        },
      },
    });
    const adminOption = wrapper
      .findAllComponents({ name: 'RouteMenuItem' })
      .map((item) => item.props('option'))
      .find((option) => option.label === '系统管理');

    expect(adminOption.children
      .filter((option) => option.isVisible())
      .map(({ label, section }) => [label, section])).toEqual([
      ['存储集群', undefined],
      ['项目组标签', '基础配置'],
      ['用户信息管理', '基础配置'],
      ['系统设置', '基础配置'],
      ['AI 中心', '智能治理'],
      ['容量预测治理', '智能治理'],
      ['事件中心', '事件与审计'],
      ['厂商事件关联目录', '事件与审计'],
      ['统一操作审计', '事件与审计'],
    ]);
  });

  it('renders each System Management classification as a single visual section label', () => {
    const visible = () => true;
    const wrapper = shallowMount(RouteMenuItem, {
      props: {
        option: {
          index: '/admin',
          label: '系统管理',
          isVisible: visible,
          children: [
            { index: '/admin/storage-clusters', label: '存储集群', isVisible: visible },
            { index: '/admin/group-tags', label: '项目组标签', section: '基础配置', isVisible: visible },
            { index: '/admin/users', label: '用户信息管理', section: '基础配置', isVisible: visible },
            { index: '/admin/ai-center', label: 'AI 中心', section: '智能治理', isVisible: visible },
            { index: '/admin/incidents', label: '事件中心', section: '事件与审计', isVisible: visible },
          ],
        },
      },
      global: {
        stubs: {
          ElSubMenu: {
            template: '<div class="sub-menu"><slot name="title" /><slot /></div>',
          },
          ElMenuItem: {
            template: '<div class="leaf-menu-item"><slot name="title" /><slot /></div>',
          },
        },
      },
    });

    expect(wrapper.findAll('[data-testid="menu-section"]')
      .map((section) => section.text())).toEqual([
      '基础配置',
      '智能治理',
      '事件与审计',
    ]);
  });

  it('keeps project-scoped resource deep links while hiding their root-menu entries', () => {
    const flatRoutes = routes.flatMap((route) => route.children || []);
    const usages = flatRoutes.find((route) => route.name === 'Usages');
    const groups = flatRoutes.find((route) => route.name === 'Groups');
    const capacityPredictions = flatRoutes.find((route) => route.name === 'CapacityPredictions');

    expect(usages.meta).toMatchObject({ title: '用户目录', isHidden: true });
    expect(usages.meta.isRoot).not.toBe(true);
    expect(groups.meta).toMatchObject({ title: '项目组', isHidden: true });
    expect(groups.meta.isRoot).not.toBe(true);
    expect(capacityPredictions).toEqual(expect.objectContaining({
      path: 'capacity-predictions',
      redirect: expect.anything(),
      meta: expect.objectContaining({ isHidden: true }),
    }));
    expect(capacityPredictions.meta.isRoot).not.toBe(true);
  });

  it('renders storage clusters as a direct menu item without the third-level submenu', () => {
    const router = createRouter({ history: createMemoryHistory(), routes });
    const wrapper = shallowMount(RouteMenu, {
      global: {
        plugins: [createPinia(), router],
        stubs: {
          ElMenu: { template: '<div><slot /></div>' },
          RouteMenuItem: {
            name: 'RouteMenuItem',
            props: ['option'],
            template: '<span class="menu-item">{{ option.label }}</span>',
          },
        },
      },
    });
    const adminOption = wrapper
      .findAllComponents({ name: 'RouteMenuItem' })
      .map((item) => item.props('option'))
      .find((option) => option.label === '系统管理');
    const storageOption = adminOption.children.find((option) => option.label === '存储集群');

    expect(storageOption.key).toBe('StorageClusters');
    expect(storageOption.index).toBe('/admin/storage-clusters');
    expect(storageOption.path).toBe('/admin/storage-clusters');
    expect(storageOption.children).toBeUndefined();
  });
});
