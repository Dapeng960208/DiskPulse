import { vi } from 'vitest';

describe('api/support', () => {
  it('wraps CRUD requests with prefixes and query params', async () => {
    vi.resetModules();
    vi.doMock('@/api/support/base-request', () => ({
      default: {},
    }));

    const request = {
      all: vi.fn(),
      spread: vi.fn(),
      post: vi.fn(() => Promise.resolve({ data: { ok: true } })),
      delete: vi.fn(() => Promise.resolve({ data: { ok: true } })),
      put: vi.fn(() => Promise.resolve({ data: { ok: true } })),
      patch: vi.fn(() => Promise.resolve({ data: { ok: true } })),
      get: vi.fn(() => Promise.resolve({ data: { ok: true } })),
      head: vi.fn(),
    };

    const { default: BaseApi } = await import('@/api/support/base-api');
    const { default: CrudApi } = await import('@/api/support/crud-api');
    const baseApi = new BaseApi('/users', request);
    const crudApi = new CrudApi('/projects', request);

    await baseApi.post('/login', { username: 'user' });
    await baseApi.get('/current', { page: 1 }, { headers: { foo: 'bar' } });
    await crudApi.fetch({ page: 1 });
    await crudApi.fetchById(1, { detail: true });
    await crudApi.create({ name: 'demo' });
    await crudApi.update(2, { name: 'changed' });
    await crudApi.replace(3, { name: 'next' });
    await crudApi.deleteById(4);

    expect(request.post).toHaveBeenCalledWith('/users/login', { username: 'user' }, undefined);
    expect(request.get).toHaveBeenCalledWith('/users/current', { params: { page: 1 }, headers: { foo: 'bar' } });
    expect(request.get).toHaveBeenCalledWith('/projects', { params: { page: 1 } });
    expect(request.get).toHaveBeenCalledWith('/projects/1', { params: { detail: true } });
    expect(request.patch).toHaveBeenCalledWith('/projects/2', { name: 'changed' }, undefined);
    expect(request.put).toHaveBeenCalledWith('/projects/3', { name: 'next' }, undefined);
    expect(request.delete).toHaveBeenCalledWith('/projects/4', undefined);
  });

  it('download() fetches a blob and never leaks the token in the URL', async () => {
    vi.resetModules();
    vi.doMock('@/api/support/base-request', () => ({ default: {} }));

    const blob = new Blob(['file-content'], { type: 'text/csv' });
    const request = {
      get: vi.fn(() => Promise.resolve({
        data: blob,
        headers: { 'content-disposition': "attachment; filename=\"report.csv\"" },
      })),
    };

    const { default: BaseApi } = await import('@/api/support/base-api');
    const baseApi = new BaseApi('/reports', request);

    const objectUrl = 'blob:mock-url';
    const createObjectURL = vi.fn(() => objectUrl);
    const revokeObjectURL = vi.fn();
    window.URL.createObjectURL = createObjectURL;
    window.URL.revokeObjectURL = revokeObjectURL;
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    const trigger = await baseApi.download('/file', { id: 1 });

    // blob 请求携带鉴权头，URL 中不含 token
    expect(request.get).toHaveBeenCalledWith('/reports/file', {
      params: { id: 1 },
      responseType: 'blob',
    });
    expect(createObjectURL).toHaveBeenCalledWith(blob);

    trigger();
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith(objectUrl);

    clickSpy.mockRestore();
  });

  it('builds request interceptors and handles response errors', async () => {
    vi.resetModules();
    const requestHandlers = {};
    const responseHandlers = {};
    const service = {
      interceptors: {
        request: {
          use: vi.fn((onFulfilled, onRejected) => {
            requestHandlers.fulfilled = onFulfilled;
            requestHandlers.rejected = onRejected;
          }),
        },
        response: {
          use: vi.fn((onFulfilled, onRejected) => {
            responseHandlers.fulfilled = onFulfilled;
            responseHandlers.rejected = onRejected;
          }),
        },
      },
    };

    vi.doMock('axios', () => ({
      default: {
        create: vi.fn(() => service),
        all: vi.fn(),
        spread: vi.fn(),
      },
    }));
    const errorMessage = vi.fn();
    const alert = vi.fn();
    vi.doMock('element-plus', () => ({
      ElMessage: {
        error: errorMessage,
      },
      ElMessageBox: {
        alert,
      },
    }));
    const push = vi.fn();
    vi.doMock('@/router', () => ({
      default: { push },
    }));
    vi.doMock('@/utils/authorization', () => ({
      getToken: () => 'auth-token',
    }));

    const { default: RequestBuilder } = await import('@/api/support/request-builder');
    const builder = new RequestBuilder({ baseURL: '/api' });
    const builtService = builder.build();
    const config = requestHandlers.fulfilled({ headers: {} });

    expect(builtService).toBe(service);
    expect(config.headers.Authorization).toBe('Bearer auth-token');

    await expect(responseHandlers.rejected({ message: 'network', config: {} })).rejects.toBeTruthy();
    expect(errorMessage).toHaveBeenCalled();

    await expect(responseHandlers.rejected({
      response: {
        status: 403,
        data: {},
        config: {},
      },
      config: {},
    })).rejects.toBeTruthy();
    expect(alert).toHaveBeenCalled();

    vi.resetModules();
  });
});
