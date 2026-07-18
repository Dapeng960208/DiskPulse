import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';
import ClusterIncidentsTab from '@/pages/admin/storage-cluster/components/ClusterIncidentsTab.vue';

const incidentApi = vi.hoisted(() => ({
  fetchIncidents: vi.fn(),
  fetchForecasts: vi.fn(),
  fetchAnomalies: vi.fn(),
}));
vi.mock('@/api/incident-api.js', () => ({ default: incidentApi }));

describe('ClusterIncidentsTab', () => {
  beforeEach(() => {
    incidentApi.fetchIncidents.mockResolvedValue({
      total: 1,
      content: [{ id: 7, display_name: 'volume-a', category: 'performance_contention', status: 'open' }],
    });
    incidentApi.fetchForecasts.mockResolvedValue({ total: 2, content: [] });
    incidentApi.fetchAnomalies.mockResolvedValue({ total: 3, content: [] });
  });

  it('loads only incidents associated with the current storage cluster', async () => {
    const wrapper = shallowMount(ClusterIncidentsTab, {
      props: { clusterId: 42 },
      global: {
        directives: { loading: () => {} },
        stubs: {
          ElTable: { props: ['data'], template: '<div>{{ JSON.stringify(data) }}<slot /></div>' },
          ElTableColumn: { template: '<div />' },
          ElPagination: { template: '<div />' },
          ElTag: { template: '<span><slot /></span>' },
        },
      },
    });
    await flushPromises();

    expect(incidentApi.fetchIncidents).toHaveBeenCalledWith({ storage_cluster_id: 42, page: 1, size: 20 });
    expect(wrapper.text()).toContain('volume-a');
    expect(wrapper.text()).toContain('容量预测');
    expect(wrapper.text()).toContain('性能异常');
  });
});
