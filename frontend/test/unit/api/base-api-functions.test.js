import { vi } from 'vitest';

describe('BaseApi helper methods', () => {
  it('delegates low-level helpers and blob export requests', async () => {
    vi.resetModules();
    vi.doMock('@/api/support/base-request', () => ({
      default: {},
    }));

    const request = {
      all: vi.fn((apis) => Promise.all(apis)),
      spread: vi.fn((callback) => callback),
      post: vi.fn(() => Promise.resolve({ data: { ok: true } })),
      delete: vi.fn(() => Promise.resolve({ data: { ok: true } })),
      put: vi.fn(() => Promise.resolve({ data: { ok: true } })),
      patch: vi.fn(() => Promise.resolve({ data: { ok: true } })),
      get: vi.fn(() => Promise.resolve({ data: { ok: true } })),
      head: vi.fn(),
    };

    const { default: BaseApi } = await import('@/api/support/base-api');
    const baseApi = new BaseApi('/reports', request);

    const spreadCallback = vi.fn((left, right) => left + right);
    const spread = baseApi.$spread(spreadCallback);

    expect(await baseApi.$all(Promise.resolve(1), Promise.resolve(2))).toEqual([1, 2]);
    expect(request.all).toHaveBeenCalled();
    expect(baseApi.$post('/raw', { id: 1 })).resolves.toEqual({ data: { ok: true } });
    expect(baseApi.$delete('/raw')).resolves.toEqual({ data: { ok: true } });
    expect(baseApi.$put('/raw', { id: 2 })).resolves.toEqual({ data: { ok: true } });
    expect(baseApi.$patch('/raw', { id: 3 })).resolves.toEqual({ data: { ok: true } });
    expect(baseApi.$get('/raw')).resolves.toEqual({ data: { ok: true } });
    expect(baseApi.addPrefix('/daily')).toBe('/reports/daily');

    expect(spread(2, 3)).toBe(5);
    expect(request.spread).toHaveBeenCalledWith(spreadCallback);

    await baseApi.export('/daily', { page: 1 }, { headers: { foo: 'bar' } });
    expect(request.get).toHaveBeenCalledWith('/reports/daily', {
      headers: { foo: 'bar' },
      params: { page: 1 },
      responseType: 'blob',
    });
  });
});
