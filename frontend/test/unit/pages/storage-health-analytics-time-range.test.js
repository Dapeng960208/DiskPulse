import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';
import ClusterCapacityTab from '@/pages/admin/storage-cluster/components/ClusterCapacityTab.vue';
import ClusterFaultsTab from '@/pages/admin/storage-cluster/components/ClusterFaultsTab.vue';
import ClusterPerformanceTab from '@/pages/admin/storage-cluster/components/ClusterPerformanceTab.vue';

const storageClusterApi = vi.hoisted(() => ({
  fetchCapacityChange: vi.fn(),
  fetchErrorSeverity: vi.fn(),
  fetchTopLatency: vi.fn(),
  fetchRepeatedFaults: vi.fn(),
  fetchSystemEvents: vi.fn(),
}));

vi.mock('@/api/storage-cluster-api', () => ({ default: storageClusterApi }));

const localRange = ['2026-07-24 08:27:54', '2026-07-24 16:27:54'];
const utcRange = ['2026-07-24T00:27:54Z', '2026-07-24T08:27:54Z'];
const mountOptions = {
  props: { clusterId: 1, dateRange: localRange },
};

describe('storage health analytics time range contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    storageClusterApi.fetchCapacityChange.mockResolvedValue({ data: [] });
    storageClusterApi.fetchErrorSeverity.mockResolvedValue({ counts: {}, total: 0 });
    storageClusterApi.fetchTopLatency.mockResolvedValue({ supported: true, data: [] });
    storageClusterApi.fetchRepeatedFaults.mockResolvedValue({ data: [] });
    storageClusterApi.fetchSystemEvents.mockResolvedValue({
      data: [], total: 0, page: 1, page_size: 20,
    });
  });

  it('sends UTC bounds to every health analytics endpoint', async () => {
    const capacity = shallowMount(ClusterCapacityTab, mountOptions);
    await flushPromises();
    expect(storageClusterApi.fetchCapacityChange).toHaveBeenCalledWith(1, {
      start_time: utcRange[0],
      end_time: utcRange[1],
    });
    capacity.unmount();

    const performance = shallowMount(ClusterPerformanceTab, mountOptions);
    await flushPromises();
    expect(storageClusterApi.fetchTopLatency).toHaveBeenCalledWith(1, {
      start_time: utcRange[0],
      end_time: utcRange[1],
      object_type: 'volume',
      limit: 10,
    });
    performance.unmount();

    const faults = shallowMount(ClusterFaultsTab, mountOptions);
    await flushPromises();
    expect(storageClusterApi.fetchErrorSeverity).toHaveBeenCalledWith(1, {
      start_time: utcRange[0],
      end_time: utcRange[1],
    });
    expect(storageClusterApi.fetchRepeatedFaults).toHaveBeenCalledWith(1, {
      start_time: utcRange[0],
      end_time: utcRange[1],
    });
    expect(storageClusterApi.fetchSystemEvents).toHaveBeenCalledWith(1, {
      start_time: utcRange[0],
      end_time: utcRange[1],
      page: 1,
      page_size: 20,
    });
    faults.unmount();
  });
});
