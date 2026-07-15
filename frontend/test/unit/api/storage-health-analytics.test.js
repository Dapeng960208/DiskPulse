import { vi } from 'vitest';

vi.mock('@/api/support/base-request', () => ({ default: {} }));

const { default: BaseApi } = await import('@/api/support/base-api');
const { default: storageClusterApi } = await import('@/api/storage-cluster-api');

describe('storage cluster health analytics api', () => {
  const query = {
    start_time: '2026-07-01 00:00:00',
    end_time: '2026-07-02 00:00:00',
  };

  afterEach(() => vi.restoreAllMocks());

  it.each([
    ['fetchCapacityChange', 'capacity-change'],
    ['fetchErrorSeverity', 'error-severity'],
    ['fetchTopLatency', 'top-latency'],
    ['fetchRepeatedFaults', 'repeated-faults'],
  ])('maps %s to its analytics endpoint', async (method, endpoint) => {
    const getSpy = vi.spyOn(BaseApi.prototype, 'get').mockResolvedValue({});

    await storageClusterApi[method](7, query);

    expect(getSpy).toHaveBeenCalledWith(`/7/analytics/${endpoint}`, query);
  });

  it('requests analytics exports as blobs', async () => {
    const exportSpy = vi.spyOn(BaseApi.prototype, 'export').mockResolvedValue({});
    const params = { ...query, section: 'all', format: 'excel' };

    await storageClusterApi.exportAnalytics(7, params);

    expect(exportSpy).toHaveBeenCalledWith('/7/analytics/export', params);
  });
});
