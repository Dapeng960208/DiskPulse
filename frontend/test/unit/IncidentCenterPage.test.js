import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';
import IncidentCenterPage from '@/pages/incident/IncidentCenterPage.vue';

const incidentApi = vi.hoisted(() => ({
  fetchIncidents: vi.fn(),
  updateIncident: vi.fn(),
  createComment: vi.fn(),
  createMaintenanceWindow: vi.fn(),
}));

vi.mock('@/api/incident-api.js', () => ({ default: incidentApi }));

const passthrough = (name, tag = 'div') => ({
  name,
  inheritAttrs: false,
  template: `<${tag}><slot /></${tag}>`,
});

async function mountPage() {
  const wrapper = shallowMount(IncidentCenterPage, {
    global: {
      stubs: {
        QueryForm: passthrough('QueryForm', 'form'),
        DataTable: {
          name: 'DataTable',
          props: { data: { type: Array, default: () => [] } },
          template: '<div>{{ JSON.stringify(data) }}<slot /></div>',
        },
        ElFormItem: passthrough('ElFormItem'),
        ElInput: passthrough('ElInput', 'input'),
        ElSelect: passthrough('ElSelect', 'select'),
        ElOption: passthrough('ElOption', 'option'),
        ElTableColumn: { name: 'ElTableColumn', template: '<div />' },
        ElPagination: passthrough('ElPagination'),
        ElButton: passthrough('ElButton', 'button'),
        ElTag: passthrough('ElTag'),
      },
      directives: { loading: () => {} },
    },
  });
  await flushPromises();
  return wrapper;
}

describe('IncidentCenterPage', () => {
  beforeEach(() => {
    incidentApi.fetchIncidents.mockResolvedValue({
      total: 1,
      content: [{
        id: 1,
        display_name: 'project-alpha',
        category: 'device_fault',
        severity: 'critical',
        status: 'open',
        last_evidence_at: '2026-07-18T08:00:00Z',
      }],
    });
  });

  it('renders the incident center and its project-scoped incident list', async () => {
    const wrapper = await mountPage();

    expect(wrapper.text()).toContain('project-alpha');
    expect(incidentApi.fetchIncidents).toHaveBeenCalledWith(expect.objectContaining({ page: 1, size: 20 }));
  });

  it('resets filters, updates pagination, and opens incident details', async () => {
    const wrapper = await mountPage();
    wrapper.vm.queryParams.status = 'open';
    wrapper.vm.queryParams.category = 'device_fault';

    wrapper.vm.reset();
    await flushPromises();
    wrapper.vm.updatePagination({ page: 3, pageSize: 50 });
    await flushPromises();
    wrapper.vm.openDetail({ id: 9, status: 'investigating' });

    expect(wrapper.vm.queryParams).toMatchObject({ page: 3, size: 50, status: '', category: '' });
    expect(incidentApi.fetchIncidents).toHaveBeenLastCalledWith(expect.objectContaining({ page: 3, size: 50 }));
    expect(wrapper.vm.selectedIncident).toMatchObject({ id: 9 });
    expect(wrapper.vm.detailVisible).toBe(true);
  });

  it('wires filter and drawer v-model events to page state', async () => {
    const wrapper = await mountPage();
    const selects = wrapper.findAllComponents({ name: 'ElSelect' });

    await selects[0].vm.$emit('update:modelValue', 'resolved');
    await selects[1].vm.$emit('update:modelValue', 'capacity_pressure');
    await wrapper.findComponent({ name: 'QueryForm' }).vm.$emit('query');
    await wrapper.findComponent({ name: 'IncidentDetailDrawer' }).vm.$emit('update:modelValue', true);
    await flushPromises();

    expect(wrapper.vm.queryParams).toMatchObject({ page: 1, status: 'resolved', category: 'capacity_pressure' });
    expect(wrapper.vm.detailVisible).toBe(true);
    expect(incidentApi.fetchIncidents).toHaveBeenLastCalledWith(expect.objectContaining({
      status: 'resolved',
      category: 'capacity_pressure',
    }));
  });
});
