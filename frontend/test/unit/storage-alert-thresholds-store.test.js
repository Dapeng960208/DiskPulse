import { createPinia, setActivePinia } from 'pinia';
import { useStorageAlertThresholds } from '@/stores/storage-alert-thresholds';

const configApi = vi.hoisted(() => ({
  fetchStorageAlertThresholds: vi.fn(),
}));

vi.mock('@/api/config-api', () => ({ default: configApi }));

describe('storage alert threshold store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('loads global thresholds once for concurrent progress components', async () => {
    configApi.fetchStorageAlertThresholds.mockResolvedValue({
      important: 70,
      serious: 85,
      emergency: 93,
    });
    const store = useStorageAlertThresholds();

    await Promise.all([store.load(), store.load(), store.load()]);

    expect(configApi.fetchStorageAlertThresholds).toHaveBeenCalledTimes(1);
    expect(store.thresholds).toEqual({ important: 70, serious: 85, emergency: 93 });
  });

  it('keeps default thresholds when loading fails', async () => {
    configApi.fetchStorageAlertThresholds.mockRejectedValue(new Error('offline'));
    const store = useStorageAlertThresholds();

    await expect(store.load()).resolves.toEqual({ important: 80, serious: 90, emergency: 95 });
    expect(store.thresholds).toEqual({ important: 80, serious: 90, emergency: 95 });
  });

  it('updates cached thresholds from a saved system rule', () => {
    const store = useStorageAlertThresholds();

    store.setFromRule({
      important: { threshold: 75 },
      serious: { threshold: 88 },
      emergency: { threshold: 96 },
    });

    expect(store.thresholds).toEqual({ important: 75, serious: 88, emergency: 96 });
  });
});
