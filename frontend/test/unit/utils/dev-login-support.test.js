import { vi } from 'vitest';

const setToken = vi.fn();

vi.mock('@/utils/authorization', () => ({
  setToken,
}));

const { enableLoginSupport, isInIframe } = await import('@/utils/dev-login-support');

describe('utils/dev-login-support', () => {
  beforeEach(() => {
    setToken.mockReset();
  });

  it('applies login token from the query string in dev mode', () => {
    const originalLocation = window.location;
    delete window.location;
    window.location = { search: '?_token=test-token' };

    enableLoginSupport();

    expect(setToken).toHaveBeenCalledWith('test-token');
    window.location = originalLocation;
  });

  it('detects iframe embedding', () => {
    expect(isInIframe()).toBe(false);
  });
});
