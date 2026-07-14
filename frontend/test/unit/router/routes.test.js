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
        'StorageEnvironments',
        'AdminDashboard',
        'Aggregates',
        'Volumes',
        'Qtrees',
        'UsersManagement',
        'BackUp',
        'Settings',
      ]),
    );

    const storageEnvironmentRoute = adminRoute.children.find(
      (route) => route.name === 'StorageEnvironments',
    );
    expect(storageEnvironmentRoute).toEqual(expect.objectContaining({
      path: 'storage-environments',
      meta: expect.objectContaining({ title: '存储环境' }),
    }));
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
