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
      ai_assessment: {
        classification: 'normal_fluctuation',
        urgency: 'low',
        summary: '低负载 IOPS 短时波动，暂无服务影响证据。',
        evidence_basis: ['绝对 IOPS 低于动态噪声门槛'],
        investigation_steps: ['继续观察下一采集周期'],
        resolution_steps: ['无需设备写操作'],
        analyzed_at: '2026-07-23T06:45:00Z',
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
    expect(wrapper.findComponent({ name: 'ElDrawer' }).attributes('title')).toBe('设备健康风险 #9');
    expect(wrapper.text()).toContain('确定性诊断');
    expect(wrapper.text()).toContain('AI 处置建议');
    expect(wrapper.text()).toContain('低负载 IOPS 短时波动');
    const diagnosisTooltip = wrapper.findAllComponents({ name: 'ElTooltip' })
      .find((tooltip) => tooltip.text().includes('确定性诊断'));
    expect(diagnosisTooltip.attributes('content')).toBe('由服务端按固定证据权重计算，不使用 AI 自由生成结论。');
    expect(wrapper.text()).toContain('认领');
    expect(wrapper.text()).toContain('创建维护窗口');

    await wrapper.get('[data-testid="incident-claim"]').trigger('click');
    await flushPromises();
    expect(incidentApi.updateIncident).toHaveBeenCalledWith(9, { claim: true });
    expect(ElMessage.success).toHaveBeenCalledWith('事件已认领');
  });

  it('identifies an AI review that is currently running before an assessment is available', async () => {
    incidentApi.fetchIncident.mockResolvedValueOnce({
      ...incident,
      evidence: [],
      timeline: [],
      diagnosis: null,
      ai_assessment: null,
      ai_review: {
        status: 'running',
        trigger: 'lifecycle',
        started_at: '2026-07-23T06:45:00Z',
        completed_at: null,
      },
    });

    const wrapper = await mountDrawer();

    expect(wrapper.text()).toContain('AI 正在审查');
    expect(wrapper.text()).toContain('事件触发');
    expect(wrapper.text()).toContain('2026-07-23 14:45:00');
  });

  it('only shows claim before assignment and only shows release when the current user can release it', async () => {
    incidentApi.fetchIncident.mockResolvedValueOnce({
      ...incident,
      assigned_user_id: 7,
      capabilities: { edit: true, claim: false, release: true, create_maintenance_window: true },
      evidence: [],
      timeline: [],
      diagnosis: null,
    });
    const wrapper = await mountDrawer();

    expect(wrapper.find('[data-testid="incident-claim"]').exists()).toBe(false);
    await wrapper.get('[data-testid="incident-release"]').trigger('click');
    await flushPromises();

    expect(incidentApi.updateIncident).toHaveBeenCalledWith(9, { claim: false });
    expect(ElMessage.success).toHaveBeenCalledWith('事件已释放');
  });

  it('explains incident actions in tooltips', async () => {
    const wrapper = await mountDrawer();

    const tooltipContents = wrapper.findAllComponents({ name: 'ElTooltip' })
      .map((tooltip) => tooltip.attributes('content'));
    expect(tooltipContents).toEqual(expect.arrayContaining([
      '将事件指派给当前登录用户，明确处理责任。',
      '恢复派生事件的后续通知，不删除事件、证据或原始告警。',
    ]));
  });

  it('explains the effective capacity alert threshold precedence', async () => {
    incidentApi.fetchIncident.mockResolvedValueOnce({
      ...incident,
      category: 'capacity_pressure',
      evidence: [],
      timeline: [],
      diagnosis: null,
    });
    const wrapper = await mountDrawer();

    const tooltipContents = wrapper.findAllComponents({ name: 'ElTooltip' })
      .map((tooltip) => tooltip.attributes('content'));
    expect(tooltipContents).toContain('容量预测显示可能耗尽，或当前资源的有效告警规则达到阈值。默认按硬限额 80%/90%/95%；用户目录优先采用项目组规则，其次项目规则，最后系统规则。');
  });

  it('uses clear Chinese terms for the affected object, event type, and monitoring blind spot', async () => {
    incidentApi.fetchIncident.mockResolvedValueOnce({
      ...incident,
      category: 'telemetry_blindspot',
      evidence: [],
      timeline: [],
      diagnosis: null,
    });
    const wrapper = await mountDrawer();

    const descriptionLabels = wrapper.findAllComponents({ name: 'ElDescriptionsItem' })
      .map((item) => item.attributes('label'));
    const tooltipContents = wrapper.findAllComponents({ name: 'ElTooltip' })
      .map((tooltip) => tooltip.attributes('content'));
    expect(descriptionLabels).toEqual(expect.arrayContaining(['受影响对象', '事件类型']));
    expect(wrapper.text()).toContain('监控盲区');
    expect(tooltipContents).toContain('监控盲区：容量、厂商事件或性能监控采集过期、采集失败或覆盖率不足，当前数据不足以可靠判断资产状态。');
    expect(tooltipContents.join('')).not.toContain('遥测');
  });

  it('states the performance anomaly theme and labels the actual association content', async () => {
    incidentApi.fetchIncident.mockResolvedValueOnce({
      ...incident,
      category: 'performance_contention',
      display_name: '/ifs/data/IC/tmpdata/project/SPA3610',
      evidence: [{
        id: 1204,
        source: 'anomaly_observation',
        source_ref: 'anomaly:1204',
        evidence_type: 'continuous_performance_anomaly',
        observed_at: '2026-07-23T09:45:00Z',
        presentation: {
          group_key: 'anomaly_observation',
          group_label: '性能异常',
          title: '持续性能异常',
          summary: 'P95 总延迟连续三个相邻 5 分钟窗口超出基于过去 28 天同星期同小时历史样本计算的正常参考范围。',
          scope_label: 'P95 总延迟',
          technical_ref: 'anomaly:1204',
          metric_key: 'latency',
          metric_label: 'P95 总延迟',
          metric_unit: 'ms',
          window_start: '2026-07-23T09:35:00Z',
          window_end: '2026-07-23T09:45:00Z',
          observed_value: 24.5,
          baseline_value: 10,
          reference_lower: 0,
          reference_upper: 20.38,
          robust_z_score: 4.89,
          reference_purpose: '该标识用于把事件证据与原始异常观测精确关联，支持去重、审计和回放；它本身不是异常结论。',
          lookup_hint: 'anomaly:1204 中的数字部分是异常观测 ID 1204。可在性能异常接口按存储集群、metric=latency 和异常时间范围筛选后，以 id=1204 精确核对。',
        },
      }],
      timeline: [{
        id: 13,
        event_type: 'evidence_added',
        occurred_at: '2026-07-23T09:50:56Z',
        presentation: {
          action_label: '关联新证据',
          summary: '关联关联事件证据：系统已关联一条待核查的事件证据。',
          actor_label: '系统',
        },
      }],
      diagnosis: null,
    });
    const wrapper = await mountDrawer();

    expect(wrapper.findComponent({ name: 'ElDrawer' }).attributes('title')).toBe('性能异常 #9');
    expect(wrapper.findAllComponents({ name: 'ElDescriptionsItem' })
      .map((item) => item.attributes('label'))).toContain('事件主题');
    expect(wrapper.text()).toContain('性能异常 · /ifs/data/IC/tmpdata/project/SPA3610');
    expect(wrapper.text()).toContain('持续性能异常');
    expect(wrapper.text()).toContain('P95 总延迟连续三个相邻 5 分钟窗口超出基于过去 28 天同星期同小时历史样本计算的正常参考范围。');
    expect(wrapper.text()).toContain('性能指标');
    expect(wrapper.text()).toContain('P95 总延迟');
    expect(wrapper.text()).toContain('异常时间范围');
    expect(wrapper.text()).toContain('2026-07-23 17:35:00 至 2026-07-23 17:45:00');
    expect(wrapper.text()).toContain('窗口末点 P95');
    expect(wrapper.text()).toContain('24.50 ms');
    expect(wrapper.text()).toContain('历史基线');
    expect(wrapper.text()).toContain('10.00 ms');
    expect(wrapper.text()).toContain('正常参考范围');
    expect(wrapper.text()).toContain('0.00–20.38 ms');
    expect(wrapper.text()).toContain('鲁棒 Z 分数 4.89');
    expect(wrapper.text()).toContain('系统新增一项性能异常关联证据；具体类型、内容和影响范围见上方“关联证据”。');
    expect(wrapper.text()).not.toContain('关联关联事件证据');
    const evidenceLabels = wrapper.findAll('.incident-detail__evidence-item dt')
      .map((item) => item.text());
    expect(evidenceLabels).toContain('关联类型');
    expect(evidenceLabels).toContain('关联内容');
    expect(evidenceLabels).not.toContain('异常说明');
    const technicalDetails = wrapper.find('details').text();
    expect(technicalDetails).toContain('证据标识');
    expect(technicalDetails).toContain('标识作用');
    expect(technicalDetails).toContain('回查方式');
    expect(technicalDetails).toContain('异常观测 ID 1204');
    expect(technicalDetails).not.toContain('关联对象');
    expect(technicalDetails).not.toContain('证据范围');
    expect(technicalDetails).not.toContain('证据类型');
  });

  it('orders evidence and timeline from newest to oldest, and labels the technical association', async () => {
    incidentApi.fetchIncident.mockResolvedValueOnce({
      ...incident,
      category: 'telemetry_blindspot',
      evidence: [
        {
          id: 1,
          source: 'telemetry_quality',
          source_ref: 'quality:7:performance:2026-07-20T06:15:00+00:00:telemetry_stale',
          evidence_type: 'telemetry_stale',
          observed_at: '2026-07-20T06:15:00Z',
          presentation: {
            group_key: 'telemetry_quality',
            group_label: '监控可用性异常',
            title: '性能采集已过期',
            scope_label: '性能采集',
            summary: '性能采集自 2026-07-20 06:15 起未产生新的成功采集记录。',
            technical_ref: 'quality:7:performance:2026-07-20T06:15:00+00:00:telemetry_stale',
          },
        },
        {
          id: 2,
          source: 'telemetry_quality',
          source_ref: 'quality:7:performance:2026-07-20T07:15:00+00:00:coverage_insufficient',
          evidence_type: 'coverage_insufficient',
          observed_at: '2026-07-20T07:15:00Z',
          presentation: {
            group_key: 'telemetry_quality',
            group_label: '监控可用性异常',
            title: '性能采集覆盖不足',
            scope_label: '性能采集',
            summary: '性能采集覆盖率低于要求。',
            technical_ref: 'quality:7:performance:2026-07-20T07:15:00+00:00:coverage_insufficient',
          },
        },
      ],
      timeline: [
        {
          id: 1,
          event_type: 'created',
          occurred_at: '2026-07-20T06:07:56Z',
          presentation: {
            action_label: '系统创建事件',
            summary: '系统根据关联证据创建了该事件。',
            actor_label: '系统',
          },
        },
        {
          id: 2,
          event_type: 'evidence_added',
          occurred_at: '2026-07-20T07:15:00Z',
          presentation: {
            action_label: '关联新证据',
            summary: '关联性能采集覆盖不足。',
            actor_label: '系统',
          },
        },
      ],
      diagnosis: null,
    });
    const wrapper = await mountDrawer();

    expect(wrapper.text()).toContain('关联概览');
    expect(wrapper.text()).toContain('监控可用性异常');
    expect(wrapper.text()).toContain('性能采集已过期');
    expect(wrapper.text()).toContain('性能采集覆盖不足');
    expect(wrapper.text()).toContain('性能采集自 2026-07-20 06:15 起未产生新的成功采集记录。');
    expect(wrapper.text()).toContain('系统创建事件');
    expect(wrapper.text()).not.toContain('追溯编号');
    expect(wrapper.find('details').attributes('open')).toBeUndefined();
    expect(wrapper.find('details').text()).toContain('技术关联信息');
    expect(wrapper.find('details').text()).toContain('证据标识');
    expect(wrapper.find('details').text()).toContain('标识作用');
    expect(wrapper.find('details').text()).toContain('回查方式');
    expect(wrapper.find('details').text()).not.toContain('关联对象');
    expect(wrapper.find('details').text()).not.toContain('证据范围');
    expect(wrapper.find('details').text()).not.toContain('证据类型');
    expect(wrapper.findAll('.incident-detail__evidence-item h5').map((item) => item.text())).toEqual([
      '性能采集覆盖不足',
      '性能采集已过期',
    ]);
    expect(wrapper.findAll('.incident-detail__timeline > li').map((item) => item.text())).toEqual([
      expect.stringContaining('关联新证据'),
      expect.stringContaining('系统创建事件'),
    ]);
  });

  it('shows Chinese evidence semantics and data-gap explanations without raw machine codes', async () => {
    incidentApi.fetchIncident.mockResolvedValueOnce({
      ...incident,
      evidence: [{
        id: 7,
        source: 'vendor_event',
        source_ref: 'storage_alert:91',
        evidence_type: 'severe_vendor_event',
        observed_at: '2026-07-20T07:15:00Z',
        data_gaps: [],
        presentation: {
          group_key: 'vendor_event',
          group_label: '厂商系统事件与故障日志',
          title: '认证服务查询失败',
          summary: 'NetApp 事件 secd.authsys.lookup.failed：名称服务或认证后端查询失败。',
          scope_label: '节点 node-a',
          technical_ref: 'storage_alert:91',
          association_type: 'fault_log',
          association_type_label: '故障日志',
          event_code: 'secd.authsys.lookup.failed',
          log_excerpt: 'Unable to retrieve credentials for SVM_nas',
          detail_available: true,
        },
      }],
      timeline: [],
      diagnosis: {
        confidence: 'medium',
        candidates: [],
        data_gaps: ['asset_mapping_missing'],
        data_gap_details: [{
          code: 'asset_mapping_missing',
          label: '资产映射不完整',
          description: '事件至少已归属存储集群，但节点、卷、Qtree 或项目的稳定映射链路不完整；已识别稳定节点身份的厂商事件不会产生此缺口。',
          impact: '不影响查看已规范化的厂商事件日志正文。',
        }],
      },
    });
    const wrapper = await mountDrawer();

    expect(wrapper.findComponent({ name: 'ElDrawer' }).attributes('title')).toBe('系统故障事件 #9');
    expect(wrapper.text()).toContain('厂商系统事件与故障日志');
    expect(wrapper.text()).toContain('故障日志');
    expect(wrapper.text()).toContain('认证服务查询失败');
    expect(wrapper.text()).toContain('Unable to retrieve credentials for SVM_nas');
    expect(wrapper.text()).toContain('资产映射不完整');
    expect(wrapper.text()).toContain('不影响查看已规范化的厂商事件日志正文');
    expect(wrapper.text()).not.toContain('asset_mapping_missing');
  });
});
