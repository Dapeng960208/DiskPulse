import { vi } from 'vitest';

const beforeEachHook = vi.fn();
const afterEachHook = vi.fn();
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
  useCurrentUser: () => ({
    setCurrentUser: vi.fn(),
  }),
}));

vi.mock('@/utils', () => ({
  updatePageSubtitle: vi.fn(),
}));

vi.mock('@/utils/authorization', () => ({
  hasAnyRole: vi.fn(() => true),
}));

vi.mock('@/api/users-api', () => ({
  default: {
    fetchProfile: vi.fn(() => Promise.resolve({ result: {} })),
  },
}));

describe('router/index', () => {
  it('registers navigation guards and exports a router instance', async () => {
    const { default: router } = await import('@/router/index');

    expect(createRouterMock).toHaveBeenCalled();
    expect(beforeEachHook).toHaveBeenCalled();
    expect(afterEachHook).toHaveBeenCalled();
    expect(router).toBeTruthy();
  });
});
