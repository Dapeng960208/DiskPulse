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
        'GroupTags',
        'AdminDashboard',
        'Aggregates',
        'Volumes',
        'Qtrees',
        'UsersManagement',
        'BackUp',
        'Settings',
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
