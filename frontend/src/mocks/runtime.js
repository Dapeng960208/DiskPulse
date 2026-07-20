const traceId = () => `mock-${Math.random().toString(36).slice(2, 10)}`;

export const DEMO_PASSWORD = 'Demo@2026';
export const DEMO_USERS = [
  { id: 1, username: 'demo-superadmin', commonName: '演示超级管理员', role: 'superadmin', projectIds: [1, 2] },
  { id: 2, username: 'demo-project-admin', commonName: '演示项目管理员', role: 'project_admin', projectIds: [1] },
  { id: 3, username: 'demo-editor', commonName: '演示编辑成员', role: 'editor', projectIds: [1] },
  { id: 4, username: 'demo-reader', commonName: '演示只读成员', role: 'reader', projectIds: [1] },
];

const SYSTEM_RESOURCE_PREFIXES = [
  '/storage-clusters',
  '/aggregates',
  '/volumes',
  '/qtrees',
  '/group-tags',
  '/users',
  '/storage-back-up-records',
];

const seed = () => {
  const projects = ['芯片设计平台', '企业基础设施', '智能制造平台', '云原生服务', '数据分析中心']
    .map((name, index) => ({ id: index + 1, name, description: `虚构演示项目：${name}` }));
  const clusters = ['NetApp-上海', 'NetApp-北京', 'PowerScale-研发', 'NetApp-灾备', 'PowerScale-归档']
    .map((name, index) => ({
      id: index + 1,
      name,
      project_id: null,
      storage_type: index === 2 || index === 4 ? 'isilon' : 'netapp',
      protocol: 'https',
      enabled: true,
      status: index === 3 ? 'warning' : 'healthy',
    }));
  const tags = ['研发', '生产', '测试', '归档', '共享'].map((name, index) => ({ id: index + 1, name }));
  const users = ['alice', 'bob', 'carol', 'david', 'emma'].map((rd_username, index) => ({
    id: index + 1,
    rd_username,
    username: rd_username,
    common_name: `${rd_username.toUpperCase()} 演示用户`,
    user_type: 1,
    email: `${rd_username}@example.test`,
    enabled: true,
  }));
  projects.forEach((project, index) => {
    const limit = 1200 + index * 180;
    const used = 480 + index * 130;
    const storageCluster = clusters[index];

    Object.assign(project, {
      limit,
      used,
      use_ratio: Number(((used / limit) * 100).toFixed(2)),
      storage_clusters: [storageCluster],
      storage_cluster_types: [storageCluster.storage_type],
      in_charge_user_id: users[index].id,
      in_charge_user: users[index],
    });
  });
  const groups = projects.map((project, index) => ({
    id: 11 + index,
    name: `${project.name.replace('平台', '')}项目组`,
    project_id: project.id,
    in_charge_user_id: users[index].id,
    linux_path: `/data/demo/project-${project.id}`,
    used: 260 + index * 55,
    limit: 600 + index * 80,
    use_ratio: 0.43 + index * 0.04,
    group_tag: tags[index],
    group_tag_id: tags[index].id,
    storage_cluster: clusters[index],
    storage_cluster_id: clusters[index].id,
    capabilities: {},
  }));
  const aggregates = clusters.map((cluster, index) => ({
    id: index + 1,
    name: `aggr_demo_${index + 1}`,
    storage_cluster_id: cluster.id,
    storage_cluster: cluster,
    used: 680 + index * 95,
    limit: 1200 + index * 120,
    use_ratio: 0.57 + index * 0.02,
  }));
  const volumes = clusters.map((cluster, index) => ({
    id: index + 1,
    name: `vol_demo_${index + 1}`,
    path: `/vol/demo-${index + 1}`,
    aggregate_id: aggregates[index].id,
    aggregate: aggregates[index],
    storage_cluster_id: cluster.id,
    storage_cluster: cluster,
    project_id: null,
    used: 420 + index * 60,
    limit: 800 + index * 100,
    soft_limit: 700 + index * 80,
    use_ratio: 0.52 + index * 0.03,
  }));
  const qtrees = clusters.map((cluster, index) => ({
    id: index + 1,
    name: `qt_demo_${index + 1}`,
    path: `/vol/demo-${index + 1}/qt-demo-${index + 1}`,
    volume_id: volumes[index].id,
    volume: volumes[index],
    storage_cluster_id: cluster.id,
    storage_cluster: cluster,
    project_id: null,
    used: 230 + index * 45,
    limit: 500 + index * 70,
    soft_limit: 440 + index * 60,
    use_ratio: 0.46 + index * 0.04,
  }));
  const usages = users.map((user, index) => {
    const used = 180 + index * 42;
    const limit = 450 + index * 65;
    const softLimit = 400 + index * 60;

    return {
      id: 101 + index,
      name: `home-${user.rd_username}`,
      rd_username: user.rd_username,
      user,
      project_id: projects[index].id,
      project: projects[index],
      group_id: groups[index].id,
      group: groups[index],
      group_tag_id: tags[index].id,
      group_tag: tags[index],
      linux_path: `/data/demo/project-${index + 1}/${user.rd_username}`,
      used,
      limit,
      soft_limit: softLimit,
      use_ratio: Number(((used / limit) * 100).toFixed(2)),
      soft_use_ratio: Number(((used / softLimit) * 100).toFixed(2)),
      storage_cluster: clusters[index],
      storage_cluster_id: clusters[index].id,
      capabilities: {},
    };
  });
  const incidents = ['容量压力', '磁盘故障', '性能争用', '遥测延迟', '复制滞后'].map((display_name, index) => {
    const category = ['capacity_pressure', 'device_fault', 'performance_contention', 'telemetry_blindspot', 'capacity_pressure'][index];
    const status = ['open', 'acknowledged', 'investigating', 'mitigated', 'resolved'][index];
    const lastEvidenceAt = `2026-07-18 0${9 + index}:30:00`;
    const evidence = [
      {
        id: 1001 + index * 10,
        source: 'capacity_prediction',
        source_ref: `forecast:capacity-${index + 1}`,
        evidence_type: 'forecast_exhaustion',
        observed_at: `2026-07-18 0${8 + index}:30:00`,
        data_gaps: [],
      },
      {
        id: 1002 + index * 10,
        source: 'storage_alert',
        source_ref: `alert:storage-${index + 1}`,
        evidence_type: index === 1 ? 'severe_vendor_event' : 'threshold_breach',
        observed_at: lastEvidenceAt,
        data_gaps: [],
      },
    ];
    return {
      id: 301 + index,
      project_id: projects[index].id,
      storage_cluster_id: 1,
      asset_type: 'storage_usage',
      asset_id: String(101 + index),
      vendor: index === 1 ? 'netapp' : 'diskpulse',
      display_name,
      category,
      severity: index === 1 ? 'critical' : 'warning',
      status,
      opened_at: `2026-07-18 0${8 + index}:00:00`,
      last_evidence_at: lastEvidenceAt,
      resolved_at: status === 'resolved' ? lastEvidenceAt : null,
      created_at: `2026-07-18 0${8 + index}:00:00`,
      updated_at: lastEvidenceAt,
      evidence,
      timeline: [
        {
          id: 2001 + index * 10,
          event_type: 'opened',
          actor_user_id: null,
          from_status: null,
          to_status: 'open',
          comment: '已根据关联遥测创建事件',
          occurred_at: `2026-07-18 0${8 + index}:00:00`,
        },
        {
          id: 2002 + index * 10,
          event_type: 'evidence_added',
          actor_user_id: null,
          from_status: null,
          to_status: null,
          comment: '已关联最新证据',
          occurred_at: lastEvidenceAt,
        },
      ],
      diagnosis: {
        id: 4001 + index,
        algorithm_version: 'forecast-incident-v1',
        candidates: [{
          category,
          score: index === 1 ? 0.91 : 0.78,
          evidence_refs: evidence.map((item) => item.source_ref),
          data_gaps: [],
        }],
        confidence: index === 1 ? 'high' : 'medium',
        evidence_ids: evidence.map((item) => String(item.id)),
        data_gaps: [],
        created_at: lastEvidenceAt,
      },
    };
  });
const alerts = incidents.map((incident, index) => ({
  id: index + 1,
  project_id: incident.project_id,
  storage_cluster_id: clusters[index].id,
  source: 'diskpulse',
  alert_type: 'alert',
  related_type: 'StorageUsage',
  related_id: usages[index].id,
  event_type: ['trigger', 'escalation', 'repeat', 'recovery', 'trigger'][index],
  quota_basis: index === 3 ? 'soft' : 'hard',
  delivery_status: ['sent', 'pending', 'retrying', 'sent', 'skipped'][index],
  cluster_name: clusters[index].name,
  project_name: projects[index].name,
  title: `${incident.display_name}预警`,
  description: `${usages[index].linux_path} 的 ${incident.display_name}预警`,
  alert_level: index === 1 ? 'serious' : 'important',
  threshold: [80, 90, 85, 75, 80][index],
  avg_use_ratio: 82 + index * 3,
  related_info: {
    context: {
      cluster: clusters[index].name,
      project: projects[index].name,
      group: groups[index].name,
      group_tag: tags[index].name,
      linux_path: usages[index].linux_path,
      username: users[index].rd_username,
    },
  },
  updated_at: incident.last_evidence_at,
  created_at: incident.last_evidence_at,
}));
  const audits = incidents.map((incident, index) => {
    const resource = [projects[index], usages[index], groups[index], alerts[index], { id: index + 1, title: `AI 会话 ${index + 1}` }][index];
    const resourceType = ['ProjectMembership', 'StorageUsage', 'Group', 'StorageAlert', 'AIConversation'][index];
    const action = ['project.member.read', 'storage.usage.update', 'group.quota.adjust', 'storage.alert.read', 'ai.conversation.create'][index];
    const resourceId = resource?.id || index + 1;
    return {
      id: index + 1,
      action,
      outcome: 'success',
      result: 'success',
      occurred_at: incident.last_evidence_at,
      created_at: incident.last_evidence_at,
      project_id: incident.project_id,
      project: projects[index],
      actor_user_id: users[index].id,
      actor: users[index],
      resource_type: resourceType,
      resource_id: resourceId,
      resource_name: resource?.name || resource?.title || incident.display_name,
      resource_path: resource?.linux_path || resource?.path || null,
      trace_id: `audit-trace-${index + 1}`,
      request_id: `mock-request-${index + 1}`,
      reason_code: null,
      before_summary: { action, version: 1, resource_id: resourceId },
      after_summary: { action, version: 2, resource_id: resourceId, outcome: 'success' },
      metadata: {
        client_ip: `10.20.0.${index + 11}`,
        endpoint: `/v1/${resourceType.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`).replace(/^-/, '')}/${resourceId}`,
        request_method: index === 0 || index === 3 ? 'GET' : 'PATCH',
        user_agent: 'DiskPulse Mock Console/1.0',
      },
      detail: 'Mock 演示审计记录',
    };
  });
  const aiModels = ['容量助手', '告警分析', '运维问答', '归档顾问', '报表生成'].map((name, index) => ({
    id: index + 1,
    name,
    description: `${name}演示模型`,
    provider: index === 2 ? 'ollama' : 'openai',
    model: `mock-model-${index + 1}`,
    api_key_masked: 'mock-****',
    enabled: true,
    enable_chat: true,
    temperature: 0.3,
    max_tokens: 2048,
  }));
  const capacityPredictionCandidates = [
    {
      id: 1,
      version: 'capacity-ai-v2',
      ai_model_id: 1,
      enabled: true,
      activation_ready: true,
      forecast_count: 18,
      fallback_count: 1,
      evaluations: [
        { baseline_mape: 12.4, candidate_mape: 9.8, risk_coverage_ok: true, window_start: '2026-04-01T00:00:00Z', window_end: '2026-05-01T00:00:00Z' },
        { baseline_mape: 11.9, candidate_mape: 9.2, risk_coverage_ok: true, window_start: '2026-05-01T00:00:00Z', window_end: '2026-05-31T00:00:00Z' },
        { baseline_mape: 12.1, candidate_mape: 9.4, risk_coverage_ok: true, window_start: '2026-05-31T00:00:00Z', window_end: '2026-06-30T00:00:00Z' },
      ],
    },
    {
      id: 2,
      version: 'capacity-ai-v3',
      ai_model_id: 3,
      enabled: false,
      activation_ready: false,
      forecast_count: 6,
      fallback_count: 0,
      evaluations: [
        { baseline_mape: 10.8, candidate_mape: 9.9, risk_coverage_ok: true, window_start: '2026-06-01T00:00:00Z', window_end: '2026-07-01T00:00:00Z' },
      ],
    },
  ];
  const conversations = aiModels.map((model, index) => ({
    id: index + 1,
    title: `${model.name}会话`,
    model_id: model.id,
    messages: Array.from({ length: 5 }, (_, messageIndex) => ({
      id: index * 10 + messageIndex + 1,
      role: messageIndex % 2 === 0 ? 'user' : 'assistant',
      content: `Mock ${model.name}第 ${messageIndex + 1} 条消息`,
      created_at: `2026-07-18 0${9 + messageIndex}:00:00`,
    })),
  }));

  return {
    projects,
    clusters,
    tags,
    users,
    groups,
    usages,
    aggregates,
    volumes,
    qtrees,
    incidents,
    alerts,
    audits,
    aiModels,
    capacityPredictionSettings: { visible: true },
    capacityPredictionPlans: [
      { id: 1, asset_type: 'storage_usage', asset_id: '101', project_id: 1, effective_at: '2026-08-01T00:00:00Z', capacity_delta: 80, reason: 'Mock 演示扩容计划', created_at: '2026-07-18T09:00:00Z' },
      { id: 2, asset_type: 'group', asset_id: '11', project_id: 1, effective_at: '2026-08-15T00:00:00Z', capacity_delta: 150, reason: 'Mock 演示项目组扩容计划', created_at: '2026-07-18T09:30:00Z' },
    ],
    capacityPredictionCandidates,
    conversations,
    backups: usages.map((usage, index) => ({
      id: index + 1,
      user: usage.user,
      source_path: usage.linux_path,
      destination_path: `/backup/demo/${usage.rd_username}`,
      start_time: `2026-07-1${index + 1} 01:00:00`,
      end_time: `2026-07-1${index + 1} 01:30:00`,
      status: 2,
    })),
    aiAudits: conversations.map((conversation, index) => ({
      id: index + 1,
      conversation_id: conversation.id,
      conversation: { id: conversation.id, title: conversation.title },
      user_id: users[index].id,
      user: users[index],
      model_id: conversation.model_id,
      model: aiModels.find((model) => model.id === conversation.model_id),
      status: 'succeeded',
      tool_call_count: index + 1,
      tool_names: [['list_projects'], ['list_storage_usages'], ['list_alerts'], ['get_storage_cluster'], ['list_groups']][index],
      started_at: `2026-07-18 0${9 + index}:00:00`,
      error_message: '',
    })),
    memberships: projects.map((project, index) => ({
      project_id: project.id,
      user_id: users[index].id,
      user: users[index],
      role: index === 0 ? 'project_admin' : 'member',
    })),
    config: {
      storage_alert_rule: {
        quota_basis: 'hard',
        important: { threshold: 80, repeat_hours: 24 },
        serious: { threshold: 90, repeat_hours: 6 },
        emergency: { threshold: 95, repeat_hours: 1 },
      },
    },
  };
};

function error(status, message = '没有权限') { const value = new Error(message); value.status = status; value.response = { status, data: { message } }; return value; }
function normalizePath(path) { const value = String(path || '').replace(/^https?:\/\/[^/]+/, '').replace(/^\/storage-pulse\/api/, '').split('?')[0].replace(/\/{2,}/g, '/'); return value.length > 1 ? value.replace(/\/$/, '') : value; }
function page(content, pagination) {
  const total = content.length;
  const pageNumber = Math.max(1, Number(pagination?.page) || 1);
  const pageSize = Math.max(1, Number(pagination?.size) || 20);
  const offset = (pageNumber - 1) * pageSize;
  const pageContent = pagination ? content.slice(offset, offset + pageSize) : content;
  return { content: pageContent, total, totalElements: total, data: pageContent, meta: { total }, traceId: traceId() };
}

export function createMockGateway() {
  const state = seed();
  const tokens = new Map();
  const accountFor = (token) => {
    const clean = String(token || '').replace(/^Bearer\s+/i, '');
    const username = tokens.get(clean) || clean.replace(/^mock:/, '');
    return DEMO_USERS.find((account) => account.username === username);
  };
  const profile = (account) => ({ id: account.id, commonName: account.commonName, avatarUrl: '', roleCodes: [account.role], permissionCodes: account.role === 'superadmin' ? [['*', '*', '*']] : [], extensionAttributes: {} });
  const allowed = (account, projectId) => account?.role === 'superadmin' || account?.projectIds.includes(Number(projectId));
  const capabilities = (account, projectId, groupOwnerId = null) => {
    const scoped = allowed(account, projectId);
    const projectAdmin = scoped && account.role === 'project_admin';
    return { edit: scoped && ['superadmin', 'project_admin', 'editor'].includes(account.role), manage_members: projectAdmin || account.role === 'superadmin', manage_project_admins: account.role === 'superadmin', view_audit_events: projectAdmin || account.role === 'superadmin', adjust_quota: account.role === 'superadmin' || (scoped && groupOwnerId === account.id) };
  };
  const resourceCapabilities = (account, item) => {
    const group = item?.group
      || state.groups.find((record) => record.id === Number(item?.group_id))
      || (item?.in_charge_user_id != null ? item : null);
    return capabilities(account, item?.project_id || group?.project_id || 1, group?.in_charge_user_id);
  };
  const scoped = (account, records) => account.role === 'superadmin'
    ? records
    : records.filter((record) => record.project_id != null && allowed(account, record.project_id));
  const predictionVisibleTo = (account) => account.role === 'superadmin'
    || state.capacityPredictionSettings.visible === true;
  const resourceTrend = (item) => Array.from({ length: 6 }, (_, index) => [
    `2026-07-${String(13 + index).padStart(2, '0')} 09:00:00`,
    Math.round((Number(item.used) || 200) * (0.82 + index * 0.035)),
  ]);
  const capacityPredictionResource = (assetType, assetId) => {
    const records = assetType === 'group' ? state.groups : state.usages;
    const item = records.find((record) => record.id === Number(assetId));
    if (!item) throw error(404, '容量预测资源不存在');
    return item;
  };
  const capacityPrediction = (assetType, item) => ({
    id: 1000 + item.id,
    asset_type: assetType,
    asset_id: String(item.id),
    storage_cluster_id: item.storage_cluster_id,
    project_id: item.project_id,
    vendor: 'mock',
    display_name: item.linux_path || item.name,
    training_start: '2026-06-13T09:00:00Z',
    training_end: '2026-07-18T09:00:00Z',
    hard_limit: item.limit,
    curve: resourceTrend(item).map(([observed_at, p50]) => ({ observed_at, p10: Math.round(p50 * 0.95), p50, p90: Math.round(p50 * 1.05) })),
    exhaustion_dates: { p10: '2026-09-08', p50: '2026-09-22', p90: '2026-10-06' },
    algorithm_version: 'capacity-ai-v2',
    input_quality: { status: 'ready', coverage_ratio: 0.98, sample_count: 36, latest_observed_at: '2026-07-18T09:00:00Z', forecast_fresh_at: '2026-07-18T09:05:00Z', prediction_source: 'ai_candidate', candidate_version: 'capacity-ai-v2' },
    backtest_mape: 9.8,
    created_at: '2026-07-18T09:05:00Z',
  });
  const findResource = (path, suffix) => {
    const match = path.match(new RegExp(`^/(projects|groups|storage-usages|aggregates|volumes|qtrees)/(\\d+)/${suffix}$`));
    if (!match) return null;
    const key = { projects: 'projects', groups: 'groups', 'storage-usages': 'usages', aggregates: 'aggregates', volumes: 'volumes', qtrees: 'qtrees' }[match[1]];
    return state[key].find((item) => item.id === Number(match[2]));
  };
  const request = async (method, rawPath, body, token, options = {}) => {
    const path = normalizePath(rawPath); const verb = method.toLowerCase();
    if (path === '/users/login' && verb === 'post') {
      const account = DEMO_USERS.find((item) => item.username === body?.username);
      if (!account || body?.password !== DEMO_PASSWORD) throw error(401, '用户名或密码错误');
      const value = `mock:${account.username}`; tokens.set(value, account.username); return { result: { token: value }, token: value, data: { token: value }, meta: {}, traceId: traceId() };
    }
    const account = accountFor(token); if (!account) throw error(401, '请先登录');
    if (path === '/users/current/profile') return { result: profile(account), ...profile(account), meta: {}, traceId: traceId() };
    const systemResource = SYSTEM_RESOURCE_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`))
      && !['/users/current/profile', '/users/logout'].includes(path);
    // Review source: the generic Mock table map exposed system inventory to
    // project roles. Resolution: enforce the real superadmin boundary once,
    // before list/detail/write dispatch, while preserving personal auth paths.
    if (systemResource && account.role !== 'superadmin') throw error(403);
    if (path.startsWith('/admin') && account.role !== 'superadmin') throw error(403);
    if (path === '/dashboard/summary') return {
      summary: { used_gb: 3210, limit_gb: 5200, available_gb: 1990, alert_count: state.alerts.length },
      scope: { project_name: account.role === 'superadmin' ? '全局' : '芯片设计平台' },
    };
    if (path === '/dashboard/capacity-trend') return state.projects.map((project, index) => ({
      timestamp: `2026-07-${String(14 + index).padStart(2, '0')}`, used_gb: 2780 + index * 110,
    }));
    if (path === '/dashboard/capacity-items') return state.projects.map((project, index) => ({
      name: project.name, used_gb: 360 + index * 75, available_gb: 240 + index * 25,
    }));
    if (path === '/dashboard/alert-levels') return [
      { name: '低', count: 5 }, { name: '中', count: 4 }, { name: '重要', count: 3 }, { name: '严重', count: 2 }, { name: '紧急', count: 1 },
    ];
    if (path === '/dashboard/top-users') return state.usages.map((usage) => ({ name: usage.rd_username, used_gb: usage.used }));
    if (path === '/config/storage') return state.config;
    if (path === '/config/storage-alert-thresholds') {
      const { important, serious, emergency } = state.config.storage_alert_rule;
      return {
        important: important.threshold,
        serious: serious.threshold,
        emergency: emergency.threshold,
      };
    }
    if (path === '/v1/incidents') {
      const records = scoped(account, state.incidents).filter((incident) => (
        !options.params?.storage_cluster_id
        || incident.storage_cluster_id === Number(options.params.storage_cluster_id)
      ));
      return page(records);
    }
    if (path === '/v1/forecasts' || path === '/v1/anomalies') {
      const forecastResources = [
        ...state.usages,
        ...state.groups,
        ...state.clusters,
        ...state.volumes,
        ...state.qtrees,
      ];
      const source = path.includes('forecasts')
        ? forecastResources.map((item) => capacityPrediction(
          state.usages.includes(item) ? 'storage_usage'
            : state.groups.includes(item) ? 'group'
              : state.clusters.includes(item) ? 'storage_cluster'
                : state.volumes.includes(item) ? 'volume' : 'qtree',
          item,
        ))
        : state.incidents.map((incident, index) => ({
          ...incident,
          id: `anomaly-${index + 1}`,
          predicted_at: incident.last_evidence_at,
        }));
      const records = scoped(account, source).filter((item) => (
        !options.params?.storage_cluster_id
        || item.storage_cluster_id === Number(options.params.storage_cluster_id)
      ));
      return page(records, path === '/v1/forecasts' ? options.params || {} : undefined);
    }
    if (path === '/v1/capacity-predictions/visibility') return { visible: predictionVisibleTo(account) };
    if (path === '/v1/capacity-predictions') {
      if (!predictionVisibleTo(account)) throw error(403, '容量预测已停用');
      const resources = [...state.usages, ...state.groups];
      return page(scoped(account, resources).map((item) => capacityPrediction(
        state.usages.includes(item) ? 'storage_usage' : 'group',
        item,
      )), options.params || {});
    }
    const capacityPredictionResourcePath = path.match(/^\/v1\/capacity-predictions\/(group|storage_usage)\/(\d+)(?:\/(access|plans|related-incidents))?$/);
    if (capacityPredictionResourcePath) {
      const [, assetType, assetId, endpoint] = capacityPredictionResourcePath;
      const item = capacityPredictionResource(assetType, assetId);
      if (!allowed(account, item.project_id)) throw error(403);
      if (endpoint === 'related-incidents') return state.incidents
        .filter((incident) => incident.project_id === item.project_id && incident.category === 'capacity_pressure')
        .map((incident) => ({ id: incident.id, category: incident.category, severity: incident.severity, status: incident.status, updated_at: incident.last_evidence_at, rca_confidence: 'high' }));
      if (!predictionVisibleTo(account)) throw error(403, '容量预测已停用');
      const canManagePlans = account.role === 'superadmin'
        || (allowed(account, item.project_id) && account.role === 'project_admin');
      if (endpoint === 'access') return { visible: true, can_manage_plans: canManagePlans };
      if (endpoint === 'plans') {
        if (verb === 'post') {
          if (!canManagePlans) throw error(403);
          const plan = { id: state.capacityPredictionPlans.length + 1, asset_type: assetType, asset_id: String(assetId), project_id: item.project_id, effective_at: body?.effective_at, capacity_delta: body?.capacity_delta, reason: body?.reason, created_at: '2026-07-18T10:00:00Z' };
          state.capacityPredictionPlans.push(plan);
          return plan;
        }
        return state.capacityPredictionPlans.filter((plan) => plan.asset_type === assetType && plan.asset_id === String(assetId));
      }
      return capacityPrediction(assetType, item);
    }
    const incident = path.match(/^\/v1\/incidents\/(\d+)(?:\/(diagnosis|comments))?$/);
    if (incident) {
      const item = state.incidents.find((record) => record.id === Number(incident[1]));
      if (!item || !allowed(account, item.project_id)) throw error(403);
      if (verb === 'patch' && !capabilities(account, item.project_id).edit) throw error(403);
      if (verb === 'patch' && body?.claim === true) {
        item.assigned_user_id = account.id;
      } else if (verb === 'patch' && body?.claim === false) {
        if (item.assigned_user_id != null && item.assigned_user_id !== account.id && account.role !== 'superadmin') throw error(403, '仅认领人或超级管理员可以释放事件');
        item.assigned_user_id = null;
      } else if (verb === 'patch') {
        Object.assign(item, body || {});
      }
      const incidentCapabilities = capabilities(account, item.project_id);
      return {
        ...item,
        capabilities: {
          ...incidentCapabilities,
          create_maintenance_window: ['superadmin', 'project_admin'].includes(account.role),
          claim: incidentCapabilities.edit && item.assigned_user_id == null,
          release: incidentCapabilities.edit && item.assigned_user_id != null
            && (item.assigned_user_id === account.id || account.role === 'superadmin'),
        },
      };
    }
    const realtimeItem = findResource(path, 'realtime') || findResource(path, 'storage');
    if (realtimeItem) return {
      info: realtimeItem,
      data: resourceTrend(realtimeItem),
      trend_meta: { indicator: 'used', unit: 'GiB' },
    };
    const quotaHistory = path.match(/^\/storage-usages\/(\d+)\/quota\/history$/);
    if (quotaHistory) {
      const usage = state.usages.find((item) => item.id === Number(quotaHistory[1]));
      if (!usage || !allowed(account, usage.project_id)) throw error(403);
      if (!resourceCapabilities(account, usage).adjust_quota) throw error(403);
      return [{
          id: `mock-quota-${usage.id}`,
          operation_id: `mock-quota-operation-${usage.id}`,
          occurred_at: '2026-07-18 09:30:00',
          action: 'quota.adjust',
          outcome: 'success',
          resource_type: 'storage_usage',
          resource_id: usage.id,
          project_id: usage.project_id,
          before_summary: { hard_limit: usage.limit - 50, soft_limit: usage.soft_limit - 50 },
          after_summary: { hard_limit: usage.limit, soft_limit: usage.soft_limit },
          metadata: { change_reason: 'Mock 演示配额调整', verification_source: 'post_write_readback' },
        }];
    }
    const volumeMonitoring = path.match(/^\/volumes\/(\d+)\/monitoring$/);
    if (volumeMonitoring) {
      const volume = state.volumes.find((item) => item.id === Number(volumeMonitoring[1]));
      if (!volume) throw error(404);
      const metrics = options.params?.metrics || ['latency_total', 'iops_total', 'throughput_total'];
      const points = resourceTrend(volume);
      return {
        info: volume,
        binding: { group_id: 1, group_name: '项目目录', project_id: 1, project_name: '演示项目', linux_path: '/proj/demo' },
        capacity: points,
        performance: metrics.map((metric, metricIndex) => ({ metric, unit: metric.includes('latency') ? 'ms' : metric === 'iops_total' ? 'IOPS' : 'B/s', status: 'data', match_source: 'stable_id', data: points.map(([time, value], index) => [time, Math.round(value / (metricIndex + 2) + index * 3)]) })),
      };
    }
    const projectTree = path.match(/^\/projects\/(\d+)\/storage-tree$/);
    if (projectTree) {
      const projectId = Number(projectTree[1]);
      const valueType = options.params?.value_type || 'used';
      const toTerabytes = (value) => Number(value || 0) / 1024;
      const storageNode = (record, name, path) => ({
        limit: toTerabytes(record.limit),
        soft_limit: toTerabytes(record.soft_limit),
        used: toTerabytes(record.used),
        value: toTerabytes(record[valueType]),
        name,
        path,
        used_ratio: record.use_ratio,
        soft_used_ratio: record.soft_use_ratio,
      });
      const groups = state.groups
        .filter((group) => group.project_id === projectId)
        .map((group) => ({
          ...storageNode(group, group.name, group.linux_path),
          children: state.usages
            .filter((usage) => usage.group_id === group.id)
            .map((usage) => storageNode(usage, usage.user?.rd_username || usage.rd_username || '', usage.linux_path)),
        }));
      return { data: groups };
    }
    const projectMembers = path.match(/^\/projects\/(\d+)\/members(?:\/(\d+))?$/);
    if (projectMembers) {
      const members = state.memberships.filter((member) => member.project_id === Number(projectMembers[1]));
      if (projectMembers[2]) return members.find((member) => member.user_id === Number(projectMembers[2])) || {};
      return page(members);
    }
    if (path === '/aggregates/storage-trees') return { data: state.volumes };
    const aggregateTree = path.match(/^\/aggregates\/(\d+)\/storage-tree$/);
    if (aggregateTree) return { data: state.volumes.filter((volume) => volume.aggregate_id === Number(aggregateTree[1])) };
    const clusterAnalytics = path.match(/^\/storage-clusters\/(\d+)\/analytics\/(capacity-change|error-severity|top-latency|repeated-faults|system-events|export)$/);
    if (clusterAnalytics) {
      const [, clusterId, endpoint] = clusterAnalytics;
      const resources = Array.from({ length: 5 }, (_, index) => ({
        id: Number(clusterId) * 100 + index + 1,
        name: `vol_cluster_${clusterId}_${index + 1}`,
      }));
      if (endpoint === 'capacity-change') return { data: Array.from({ length: 6 }, (_, index) => ({ updated_at: `2026-07-${String(13 + index).padStart(2, '0')} 09:00:00`, used: 420 + index * 22 })) };
      if (endpoint === 'error-severity') return { total: 5, counts: { critical: 1, error: 1, warning: 2, info: 1 }, sources: { netapp: 5 } };
      if (endpoint === 'top-latency') return { supported: true, data: resources.map((resource, index) => ({ object_id: resource.id, object_name: resource.name, p95_latency: 4 + index, avg_latency: 2 + index, max_latency: 8 + index, avg_read_latency: 1.5 + index, avg_write_latency: 2.5 + index, avg_iops: 800 + index * 120, avg_throughput: 1024 * 1024 * (index + 1) })) };
      if (endpoint === 'repeated-faults') return { data: state.incidents.map((incident) => ({ ...incident, count: 2 })) };
      if (endpoint === 'system-events') return { page: 1, page_size: 20, total: 5, data: state.incidents.map((incident, index) => ({ source: 'NetApp', severity: index === 1 ? 'critical' : 'warning', event_code: `MOCK-${index + 1}`, object_id: `volume-${index + 1}`, object_name: `vol_demo_${index + 1}`, description: `${incident.display_name}演示系统事件`, occurred_at: incident.last_evidence_at })) };
      if (endpoint === 'export' && options.responseType === 'blob') return new Blob(['DiskPulse mock analytics export']);
    }
    const projectMatch = path.match(/^\/projects\/(\d+)$/);
    if (projectMatch) { const item = state.projects.find((record) => record.id === Number(projectMatch[1])); if (!item || !allowed(account, item.id)) throw error(403); return { ...item, capabilities: capabilities(account, item.id) }; }
    if (path === '/projects') return page(scoped(account, state.projects.map((item) => ({ ...item, project_id: item.id, capabilities: capabilities(account, item.id) }))));
    if (path === '/ai/models') return state.aiModels.filter((model) => model.enabled && model.enable_chat);
    if (path === '/v1/admin/capacity-prediction-settings') {
      if (verb === 'patch') Object.assign(state.capacityPredictionSettings, { visible: body?.user_visible === true });
      return state.capacityPredictionSettings;
    }
    if (path === '/v1/admin/capacity-prediction-candidates') {
      if (verb === 'post') {
        const item = { id: state.capacityPredictionCandidates.length + 1, version: body?.version, ai_model_id: body?.ai_model_id, enabled: false, activation_ready: false, forecast_count: 0, fallback_count: 0, evaluations: [] };
        state.capacityPredictionCandidates.push(item);
        return item;
      }
      return state.capacityPredictionCandidates;
    }
    const capacityPredictionCandidate = path.match(/^\/v1\/admin\/capacity-prediction-candidates\/(\d+)\/activate$/);
    if (capacityPredictionCandidate && verb === 'post') {
      const item = state.capacityPredictionCandidates.find((record) => record.id === Number(capacityPredictionCandidate[1]));
      if (!item) throw error(404);
      state.capacityPredictionCandidates.forEach((record) => { record.enabled = record.id === item.id; });
      return item;
    }
    if (path === '/ai/conversations') {
      if (verb === 'post') { const item = { id: state.conversations.length + 1, title: body?.title || '新对话', model_id: body?.model_id || 1, messages: [] }; state.conversations.unshift(item); return item; }
      return state.conversations;
    }
    const conversation = path.match(/^\/ai\/conversations\/(\d+)(?:\/quota-confirmations\/[^/]+)?$/);
    if (conversation) {
      const item = state.conversations.find((record) => record.id === Number(conversation[1]));
      if (!item) throw error(404, '会话不存在');
      if (verb === 'delete') { state.conversations.splice(state.conversations.indexOf(item), 1); return {}; }
      return item;
    }
    if (path === '/admin/ai-models') {
      if (verb === 'post') { const item = { id: state.aiModels.length + 1, ...(body || {}) }; state.aiModels.push(item); return item; }
      return state.aiModels;
    }
    const aiModel = path.match(/^\/admin\/ai-models\/(\d+)(?:\/test)?$/);
    if (aiModel) { const item = state.aiModels.find((record) => record.id === Number(aiModel[1])); if (!item) throw error(404); if (path.endsWith('/test')) return { message: '连接成功', reply: 'Mock OK' }; if (verb === 'delete') { state.aiModels.splice(state.aiModels.indexOf(item), 1); return {}; } if (verb === 'patch') Object.assign(item, body || {}); return item; }
    if (path === '/admin/ai-audits') return page(state.aiAudits);
    const aiAudit = path.match(/^\/admin\/ai-audits\/(\d+)$/);
    if (aiAudit) return state.aiAudits.find((record) => record.id === Number(aiAudit[1])) || {};
    const tableMap = { '/groups': 'groups', '/storage-usages': 'usages', '/storage-clusters': 'clusters', '/aggregates': 'aggregates', '/volumes': 'volumes', '/qtrees': 'qtrees', '/group-tags': 'tags', '/storage-alerts': 'alerts', '/v1/audit-events': 'audits', '/storage-back-up-records': 'backups', '/users': 'users' };
    if (path === '/storage-usages/export' && options.responseType === 'blob') return new Blob(['Linux路径,已用容量\n/data/eda/alice,320'], { type: 'text/csv' });
    if (tableMap[path]) {
      const sourceRecords = state[tableMap[path]];
      const records = sourceRecords.filter((item) => {
        if (options.params?.project_id && Number(item.project_id) !== Number(options.params.project_id)) return false;
        if (options.params?.storage_cluster_id && Number(item.storage_cluster_id) !== Number(options.params.storage_cluster_id)) return false;
        if (options.params?.related_type && item.related_type !== options.params.related_type) return false;
        if (options.params?.related_id && Number(item.related_id) !== Number(options.params.related_id)) return false;
        return true;
      });
      if (verb === 'post') { if (account.role === 'reader') throw error(403); const item = { id: Math.max(0, ...sourceRecords.map((record) => record.id || 0)) + 1, project_id: body?.project_id || 1, ...(body || {}), capabilities: capabilities(account, body?.project_id || 1) }; sourceRecords.push(item); return item; }
      return page(scoped(account, records.map((item) => ({ ...item, capabilities: { ...item.capabilities, ...resourceCapabilities(account, item) } }))));
    }
    const resource = Object.entries(tableMap).find(([prefix]) => path.startsWith(`${prefix}/`));
    if (resource) {
      const [, key] = resource; const id = Number(path.slice(resource[0].length + 1)); const records = state[key]; const item = records.find((record) => record.id === id);
      if (!item || !allowed(account, item.project_id || 1)) throw error(403);
      if (verb === 'patch' || verb === 'put') { if (account.role === 'reader') throw error(403); Object.assign(item, body || {}); return item; }
      if (verb === 'delete') { if (account.role === 'reader') throw error(403); records.splice(records.indexOf(item), 1); return {}; }
      return { ...item, capabilities: { ...item.capabilities, ...resourceCapabilities(account, item) } };
    }
    if (path.includes('export') && options.responseType === 'blob') return new Blob(['DiskPulse Mock export']);
    return page(Array.from({ length: 5 }, (_, index) => ({ id: index + 1, name: `Mock 演示数据 ${index + 1}`, project_id: 1, status: 'healthy', capabilities: capabilities(account, 1) })));
  };
  return { request, login: async (username, password) => { const value = await request('post', '/users/login', { username, password }); return { token: value.token }; }, streamAiMessage: async (_token, id, content) => [{ event: 'accepted', data: { turn_id: id, message: { id: 1, content } } }, { event: 'delta', data: { turn_id: id, text: 'Mock AI 已完成容量摘要。' } }, { event: 'completed', data: { turn_id: id, message: { id: 2, content: 'Mock AI 已完成容量摘要。' } } }] };
}

let gateway;
export function mockEnabled() { return import.meta.env.VITE_USE_MOCKS === 'true'; }
export function mockGateway() { gateway ||= createMockGateway(); return gateway; }
export function mockAxiosAdapter(config) {
  const token = config.headers?.Authorization;
  const data = typeof config.data === 'string' ? JSON.parse(config.data || '{}') : config.data;
  return mockGateway().request(config.method, config.url, data, token, config).then((result) => ({
    data: result,
    status: 200,
    statusText: 'OK',
    headers: { 'x-trace-id': result.traceId || traceId() },
    config,
  }));
}
