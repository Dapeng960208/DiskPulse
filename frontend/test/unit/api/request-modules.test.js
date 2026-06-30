import { vi } from 'vitest';

const build = vi.fn(() => ({ request: true }));
const RequestBuilder = vi.fn(() => ({ build }));

vi.mock('@/api/support/request-builder', () => ({
  default: RequestBuilder,
}));

describe('api request module factories', () => {
  it('creates both base and auth request instances through RequestBuilder', async () => {
    const { default: baseRequest } = await import('@/api/support/base-request');
    const { default: authRequest } = await import('@/api/support/auth-request');

    expect(RequestBuilder).toHaveBeenCalledTimes(2);
    expect(build).toHaveBeenCalledTimes(2);
    expect(baseRequest).toEqual({ request: true });
    expect(authRequest).toEqual({ request: true });
  });
});
