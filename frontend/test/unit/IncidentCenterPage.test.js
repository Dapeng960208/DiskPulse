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
        ElForm: passthrough('ElForm', 'form'),
        ElDialog: passthrough('ElDialog'),
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
    expect(wrapper.text()).toContain('AI 处置设置');
    expect(incidentApi.fetchIncidents).toHaveBeenCalledWith(expect.objectContaining({ page: 1, size: 20 }));
  });

  it('formats the latest evidence timestamp for people instead of exposing the API timestamp', async () => {
    const wrapper = await mountPage();

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

    const wrapper = await mountPage();

    expect(wrapper.vm.incidents.map((item) => item.id)).toEqual([2, 1]);
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

  it('edits an incident severity and status, then refreshes the list', async () => {
    incidentApi.updateIncident.mockResolvedValue({ id: 9, severity: 'critical', status: 'investigating' });
    const wrapper = await mountPage();

    wrapper.vm.openEdit({ id: 9, severity: 'warning', status: 'open' });
    wrapper.vm.editForm.severity = 'critical';
    wrapper.vm.editForm.status = 'investigating';
    await wrapper.vm.saveEdit();

    expect(wrapper.vm.editVisible).toBe(false);
    expect(incidentApi.updateIncident).toHaveBeenCalledWith(9, {
      severity: 'critical',
      status: 'investigating',
    });
    expect(incidentApi.fetchIncidents).toHaveBeenCalledTimes(2);
  });
});
