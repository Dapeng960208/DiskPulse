import { beforeEach, describe, expect, it, vi } from 'vitest';

let navigationGuard;
const beforeEachHook = vi.fn((guard) => {
  navigationGuard = guard;
});
const afterEachHook = vi.fn();
const fetchProfileMock = vi.fn();
const currentUserMock = {
  id: null,
  setCurrentUser: vi.fn((profile) => {
    currentUserMock.id = profile.id;
  }),
};
const createRouterMock = vi.fn(() => ({
  beforeEach: beforeEachHook,
  afterEach: afterEachHook,
}));

vi.mock('vue-router', () => ({
  createRouter: createRouterMock,
  createWebHistory: vi.fn(() => 'history'),
}));

vi.mock('nprogress', () => ({
  default: {
    configure: vi.fn(),
    start: vi.fn(),
    done: vi.fn(),
  },
}));

vi.mock('@/router/routes', () => ({
  default: [{ path: '/', meta: {}, children: [] }],
}));

vi.mock('@/stores/current-user', () => ({
  useCurrentUser: () => currentUserMock,
}));

vi.mock('@/utils', () => ({
  updatePageSubtitle: vi.fn(),
}));

vi.mock('@/utils/authorization', () => ({
  hasAnyRole: vi.fn(() => true),
}));

vi.mock('@/api/users-api', () => ({
  default: {
    fetchProfile: fetchProfileMock,
  },
}));

describe('router/index', () => {
  beforeEach(() => {
    fetchProfileMock.mockReset();
    currentUserMock.id = null;
    currentUserMock.setCurrentUser.mockClear();
  });

  it('registers navigation guards and exports a router instance', async () => {
    const { default: router } = await import('@/router/index');

    expect(createRouterMock).toHaveBeenCalled();
    expect(beforeEachHook).toHaveBeenCalled();
    expect(afterEachHook).toHaveBeenCalled();
    expect(router).toBeTruthy();
  });

  it('reuses the profile already stored by the login page', async () => {
    fetchProfileMock.mockResolvedValue({ result: { id: 9 } });
    await import('@/router/index');
    currentUserMock.setCurrentUser({ id: 7 });

    await navigationGuard({ path: '/', meta: {} }, { path: '/login', meta: {} });

    expect(fetchProfileMock).not.toHaveBeenCalled();
  });

  it('loads the profile once when the store is empty after a refresh', async () => {
    const profile = { id: 8 };
    fetchProfileMock.mockResolvedValue({ result: profile });
    await import('@/router/index');

    await navigationGuard({ path: '/', meta: {} }, { path: '', meta: {} });

    expect(fetchProfileMock).toHaveBeenCalledTimes(1);
    expect(currentUserMock.setCurrentUser).toHaveBeenCalledWith(profile);
  });
});
