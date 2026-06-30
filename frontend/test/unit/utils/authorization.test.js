import { vi } from 'vitest';

const cookieApi = {
  get: vi.fn(),
  set: vi.fn(),
  remove: vi.fn(),
};

const currentUser = {
  id: 1,
  roleCodes: ['diskpulse:admin'],
  permissions: [
    { applicationName: 'diskpulse', resourceName: 'users', operationName: 'read' },
    { applicationName: '*', resourceName: 'groups', operationName: '*' },
  ],
};

vi.mock('js-cookie', () => ({
  default: cookieApi,
}));

vi.mock('@/stores/current-user', () => ({
  useCurrentUser: () => currentUser,
}));

const authorization = await import('@/utils/authorization');

describe('utils/authorization', () => {
  beforeEach(() => {
    cookieApi.get.mockReset();
    cookieApi.set.mockReset();
    cookieApi.remove.mockReset();
  });

  it('manages the auth token through cookies', () => {
    cookieApi.get.mockReturnValue('token-value');

    expect(authorization.getToken()).toBe('token-value');
    expect(authorization.hasToken()).toBe(true);

    authorization.setToken('next-token');
    authorization.removeToken();

    expect(cookieApi.set).toHaveBeenCalled();
    expect(cookieApi.remove).toHaveBeenCalled();
  });

  it('checks permissions with exact and wildcard matches', () => {
    expect(authorization.isAuthenticated()).toBe(true);
    expect(authorization.hasPermission('diskpulse:users:read')).toBe(true);
    expect(authorization.hasPermission('diskpulse:groups:write')).toBe(true);
    expect(authorization.hasPermission('diskpulse:users:write')).toBe(false);
    expect(authorization.hasAnyPermission(['diskpulse:users:write', 'diskpulse:users:read'])).toBe(true);
    expect(authorization.hasAllPermissions(['diskpulse:users:read', 'diskpulse:groups:delete'])).toBe(true);
  });

  it('checks roles including root fallback', () => {
    expect(authorization.hasRole('diskpulse:admin')).toBe(true);
    expect(authorization.hasAnyRole(['diskpulse:user', 'diskpulse:admin'])).toBe(true);
    expect(authorization.hasAllRoles(['diskpulse:admin'])).toBe(true);
    expect(authorization.hasRole('diskpulse:user')).toBe(false);
  });
});
