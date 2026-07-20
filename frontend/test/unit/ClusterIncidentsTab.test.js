import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';
import ClusterIncidentsTab from '@/pages/admin/storage-cluster/components/ClusterIncidentsTab.vue';

const incidentApi = vi.hoisted(() => ({
  fetchIncidents: vi.fn(),
  fetchForecasts: vi.fn(),
  fetchAnomalies: vi.fn(),
}));
vi.mock('@/api/incident-api.js', () => ({ default: incidentApi }));

const QueryForm = defineComponent({
  name: 'QueryForm',
  emits: ['query', 'reset'],
  setup(_, { slots }) {
    return () => h('form', slots.default?.());
  },
});

const Select = defineComponent({
  name: 'ElSelect',
  props: { modelValue: { type: String, default: '' } },
  emits: ['update:modelValue'],
  setup() {
    return () => h('select');
  },
});

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
          QueryForm,
          ElFormItem: { template: '<div><slot /></div>' },
          ElSelect: Select,
          ElOption: { template: '<option />' },
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

  it('formats the latest evidence timestamp for people instead of exposing the API timestamp', async () => {
    const wrapper = shallowMount(ClusterIncidentsTab, {
      props: { clusterId: 42 },
      global: {
        directives: { loading: () => {} },
        stubs: {
          QueryForm,
          ElFormItem: { template: '<div><slot /></div>' },
          ElSelect: Select,
          ElOption: { template: '<option />' },
          ElTable: { props: ['data'], template: '<div>{{ JSON.stringify(data) }}<slot /></div>' },
          ElTableColumn: { template: '<div />' },
          ElPagination: { template: '<div />' },
          ElTag: { template: '<span><slot /></span>' },
        },
      },
    });
    await flushPromises();

    expect(wrapper.vm.formatLocalDateTime('2026-07-20T20:02:01')).toBe('2026-07-20 20:02:01');
  });

  it('keeps the current page ordered by latest evidence when an API response is out of order', async () => {
    incidentApi.fetchIncidents.mockResolvedValueOnce({
      total: 2,
      content: [
        { id: 1, display_name: 'older', last_evidence_at: '2026-07-20T09:00:00Z' },
        { id: 2, display_name: 'newer', last_evidence_at: '2026-07-20T11:00:00Z' },
      ],
    });
    const wrapper = shallowMount(ClusterIncidentsTab, {
      props: { clusterId: 42 },
      global: {
        directives: { loading: () => {} },
        stubs: {
          QueryForm,
          ElFormItem: { template: '<div><slot /></div>' },
          ElSelect: Select,
          ElOption: { template: '<option />' },
          ElTable: { props: ['data'], template: '<div>{{ JSON.stringify(data) }}<slot /></div>' },
          ElTableColumn: { template: '<div />' },
          ElPagination: { template: '<div />' },
          ElTag: { template: '<span><slot /></span>' },
        },
      },
    });
    await flushPromises();

    expect(wrapper.vm.incidents.map((item) => item.id)).toEqual([2, 1]);
  });

  it('filters associated events within the tab instead of relying on the detail-level time filter', async () => {
    const wrapper = shallowMount(ClusterIncidentsTab, {
      props: { clusterId: 42 },
      global: {
        directives: { loading: () => {} },
        stubs: {
          QueryForm,
          ElFormItem: { template: '<div><slot /></div>' },
          ElSelect: Select,
          ElOption: { template: '<option />' },
          ElTable: { props: ['data'], template: '<div>{{ JSON.stringify(data) }}<slot /></div>' },
          ElTableColumn: { template: '<div />' },
          ElPagination: { template: '<div />' },
          ElTag: { template: '<span><slot /></span>' },
        },
      },
    });
    await flushPromises();

    const selects = wrapper.findAllComponents({ name: 'ElSelect' });
    await selects[0].vm.$emit('update:modelValue', 'open');
    await selects[1].vm.$emit('update:modelValue', 'device_fault');
    await wrapper.findComponent({ name: 'QueryForm' }).vm.$emit('query');
    await flushPromises();

    expect(incidentApi.fetchIncidents).toHaveBeenLastCalledWith({
      storage_cluster_id: 42,
      status: 'open',
      category: 'device_fault',
      page: 1,
      size: 20,
    });
  });
});
