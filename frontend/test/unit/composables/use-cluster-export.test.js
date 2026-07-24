import { ref } from 'vue';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useClusterExport } from '@/composables/useClusterExport';

const storageClusterApi = vi.hoisted(() => ({
  exportAnalytics: vi.fn(),
}));

vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn() } }));
vi.mock('@/api/storage-cluster-api', () => ({ default: storageClusterApi }));

describe('useClusterExport', () => {
  let clickSpy;

  beforeEach(() => {
    storageClusterApi.exportAnalytics.mockResolvedValue({
      data: new Blob(['report']),
      headers: { 'content-disposition': 'attachment; filename="storage-health.csv"' },
    });
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:report'),
      revokeObjectURL: vi.fn(),
    });
    clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  });

  afterEach(() => {
    clickSpy.mockRestore();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('exports the local range as RFC 3339 UTC bounds', async () => {
    const { handleExport } = useClusterExport({
      clusterId: ref(1),
      dateRange: ref(['2026-07-24 08:27:54', '2026-07-24 16:27:54']),
      defaultSection: 'capacity',
    });

    await handleExport('current:csv');

    expect(storageClusterApi.exportAnalytics).toHaveBeenCalledWith(1, {
      start_time: '2026-07-24T00:27:54Z',
      end_time: '2026-07-24T08:27:54Z',
      section: 'capacity',
      format: 'csv',
    });
  });
});
