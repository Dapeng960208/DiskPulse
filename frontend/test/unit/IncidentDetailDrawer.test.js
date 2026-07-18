import { flushPromises, shallowMount } from '@vue/test-utils';
import { ElMessage } from 'element-plus';
import { vi } from 'vitest';
import IncidentDetailDrawer from '@/pages/incident/components/IncidentDetailDrawer.vue';

const incidentApi = vi.hoisted(() => ({
  fetchIncident: vi.fn(),
  updateIncident: vi.fn(),
  createComment: vi.fn(),
  createMaintenanceWindow: vi.fn(),
}));

vi.mock('@/api/incident-api.js', () => ({ default: incidentApi }));

const incident = {
  id: 9,
  project_id: 2,
  status: 'open',
  category: 'device_fault',
  display_name: 'cluster-7',
  capabilities: { edit: true, create_maintenance_window: true },
};

const passthrough = (name, tag = 'div') => ({
  name,
  template: `<${tag} v-bind="$attrs"><slot /><slot name="footer" /></${tag}>`,
});

async function mountDrawer() {
  const wrapper = shallowMount(IncidentDetailDrawer, {
    props: { incident, modelValue: true },
    global: {
      stubs: {
        ElDrawer: passthrough('ElDrawer'),
        ElDialog: passthrough('ElDialog'),
        ElDescriptions: passthrough('ElDescriptions'),
        ElDescriptionsItem: passthrough('ElDescriptionsItem'),
        ElTable: passthrough('ElTable'),
        ElTableColumn: passthrough('ElTableColumn'),
        ElTag: passthrough('ElTag'),
        ElButton: passthrough('ElButton', 'button'),
        ElInput: passthrough('ElInput', 'textarea'),
        ElDatePicker: passthrough('ElDatePicker', 'input'),
        ElForm: passthrough('ElForm', 'form'),
        ElFormItem: passthrough('ElFormItem'),
        ElTooltip: passthrough('ElTooltip'),
      },
      directives: { loading: () => {} },
    },
  });
  await flushPromises();
  return wrapper;
}

describe('IncidentDetailDrawer', () => {
  beforeEach(() => {
    vi.spyOn(ElMessage, 'success').mockImplementation(() => {});
    vi.spyOn(ElMessage, 'error').mockImplementation(() => {});
    incidentApi.fetchIncident.mockResolvedValue({
      ...incident,
      evidence: [{ id: 1, source: 'vendor_event', source_ref: 'netapp:1', evidence_type: 'severe_vendor_event' }],
      timeline: [],
      diagnosis: {
        confidence: 'medium',
        candidates: [{ category: 'device_fault', score: 0.5, evidence_refs: ['netapp:1'], data_gaps: [] }],
      },
    });
    incidentApi.updateIncident.mockResolvedValue({ ...incident, status: 'acknowledged' });
    incidentApi.createComment.mockResolvedValue({ id: 2, event_type: 'commented', comment: '处理中' });
    incidentApi.createMaintenanceWindow.mockResolvedValue({ id: 3 });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads the immutable evidence summary and exposes only permitted lifecycle controls', async () => {
    const wrapper = await mountDrawer();

    expect(incidentApi.fetchIncident).toHaveBeenCalledWith(9);
    expect(wrapper.text()).toContain('确定性诊断');
    expect(wrapper.text()).toContain('认领');
    expect(wrapper.text()).toContain('创建维护窗口');

    await wrapper.get('[data-testid="incident-claim"]').trigger('click');
    await flushPromises();
    expect(incidentApi.updateIncident).toHaveBeenCalledWith(9, { claim: true });
    expect(ElMessage.success).toHaveBeenCalledWith('事件已认领');
  });

  it('explains incident actions in tooltips', async () => {
    const wrapper = await mountDrawer();

    const tooltipContents = wrapper.findAllComponents({ name: 'ElTooltip' })
      .map((tooltip) => tooltip.props('content'));
    expect(tooltipContents).toEqual(expect.arrayContaining([
      '将事件指派给当前登录用户，明确处理责任。',
      '取消当前认领；仅认领人或超级管理员可以释放。',
      '恢复派生事件的后续通知，不删除事件、证据或原始告警。',
    ]));
  });
});
