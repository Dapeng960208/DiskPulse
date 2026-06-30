import { shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';
import App from '@/App.vue';
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

    expect(loginRoute.meta.isPublic).toBe(true);
    expect(adminRoute.children.map((route) => route.name)).toEqual(
      expect.arrayContaining([
        'StorageClusters',
        'AdminDashboard',
        'Aggregates',
        'Volumes',
        'Qtrees',
        'UsersManagement',
        'BackUp',
        'Settings',
      ]),
    );
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
    expect(adminTitles).toEqual(expect.arrayContaining(['存储集群', '存储一览', '聚合', '卷', 'qtree', '账号管理', '离职备份', '系统设置']));
    expect([...rootTitles, ...adminTitles]).not.toEqual(expect.arrayContaining(['用户', 'Volume', 'Qtree']));
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
});
