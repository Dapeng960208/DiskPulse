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
        ElCard: passthrough('ElCard'),
        ElFormItem: passthrough('ElFormItem'),
        ElInput: passthrough('ElInput', 'input'),
        ElSelect: passthrough('ElSelect', 'select'),
        ElOption: passthrough('ElOption', 'option'),
        ElTable: {
          name: 'ElTable',
          props: { data: { type: Array, default: () => [] } },
          template: '<div><slot />{{ JSON.stringify(data) }}</div>',
        },
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

    expect(wrapper.text()).toContain('事件中心');
    expect(wrapper.text()).toContain('project-alpha');
    expect(incidentApi.fetchIncidents).toHaveBeenCalledWith(expect.objectContaining({ page: 1, size: 20 }));
  });
});
