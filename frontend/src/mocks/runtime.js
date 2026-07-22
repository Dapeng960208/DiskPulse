const traceId = () => `mock-${Math.random().toString(36).slice(2, 10)}`;

const CAPACITY_FIELDS = ['limit', 'soft_limit', 'used', 'allocated', 'storage_used', 'limit_gb', 'used_gb', 'available_gb', 'quota_limit_gb', 'capacity_delta', 'size', 'hard_limit', 'p10', 'p50', 'p90'];

function capacityDisplay(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  const magnitude = Math.abs(numeric);
  const divisor = magnitude > 1024 * 1024 ? 1024 * 1024 : magnitude > 1024 ? 1024 : magnitude < 1 ? 1 / 1024 : 1;
  const unit = magnitude > 1024 * 1024 ? 'PB' : magnitude > 1024 ? 'TB' : magnitude < 1 ? 'MB' : 'GB';
  return { value: Math.round((numeric / divisor) * 100) / 100, unit };
}

function withCapacity(item) {
  const capacity = Object.fromEntries(CAPACITY_FIELDS
    .filter((field) => item?.[field] != null && Number.isFinite(Number(item[field])))
    .map((field) => [field, capacityDisplay(item[field])]));
  return { ...item, capacity };
}

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

const VENDOR_ASSOCIATION_LABELS = {
  fault_log: '故障日志',
  performance_anomaly: '性能异常',
  capacity_threshold: '容量/配额阈值',
  system_activity: '系统运行事件',
  telemetry_degradation: '监控能力下降',
  unknown: '未分类厂商事件',
};

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
      limit: 2200 + index * 320,
      used: 980 + index * 150,
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
    storage_used: 180 + index * 42,
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
  [...projects, ...clusters, ...users, ...groups, ...aggregates, ...volumes, ...qtrees, ...usages]
    .forEach((item) => Object.assign(item, { capacity: withCapacity(item).capacity }));
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
    const resourceType = ['project_membership', 'storage_usage', 'group', 'storage_alert', 'ai_conversation'][index];
    const action = ['project.member.read', 'storage.usage.update', 'group.quota.adjust', 'storage.alert.read', 'ai.conversation.create'][index];
    const resourceId = resource?.id || index + 1;
    const isIndirectProjectAssociation = resourceType === 'storage_alert';
    return {
      id: index + 1,
      action,
      outcome: 'success',
      result: 'success',
      occurred_at: incident.last_evidence_at,
      created_at: incident.last_evidence_at,
      project_id: isIndirectProjectAssociation ? null : incident.project_id,
      project: isIndirectProjectAssociation ? null : projects[index],
      actor_user_id: users[index].id,
      actor: { ...users[index], display_name: users[index].rd_username || users[index].username },
      resource_type: resourceType,
      resource_id: resourceId,
      resource_name: resource?.name || resource?.title || incident.display_name,
      resource: {
        type: resourceType,
        id: String(resourceId),
        name: resource?.name || resource?.title || incident.display_name,
      },
      related_projects: isIndirectProjectAssociation ? [projects[index]] : [],
      relation_path: isIndirectProjectAssociation ? '存储告警 → 存储集群 → 项目组 → 项目' : null,
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
  audits.unshift({
    id: 99,
    action: 'storage.collection.run',
    actor_type: 'service',
    outcome: 'success',
    result: 'success',
    phase: 'result',
    occurred_at: '2026-07-20T20:33:32.932602',
    created_at: '2026-07-20T20:33:32.932602',
    project_id: null,
    project: null,
    actor_user_id: null,
    actor: null,
    resource_type: 'storage_cluster',
    resource_id: String(clusters[0].id),
    resource_name: clusters[0].name,
    resource: { type: 'storage_cluster', id: String(clusters[0].id), name: clusters[0].name },
    related_projects: projects.slice(0, 2),
    relation_path: '存储集群 → 项目组 → 项目',
    trace_id: 'mock-collection-trace-99',
    request_id: 'mock-collection-request-99',
    reason_code: null,
    before_summary: null,
    after_summary: { storage_usage_count: 12, group_count: 3 },
    metadata: null,
    detail: 'Mock 定时存储采集完成记录',
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
      ai_model_name: '容量助手',
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
      ai_model_name: '运维问答',
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
  const vendorEventDefinitions = [
    {
      id: 1,
      storage_type: 'netapp',
      event_code: 'secd.authsys.lookup.failed',
      association_type: 'fault_log',
      title_zh: 'UNIX 用户凭据查询失败',
      description_zh: '访问请求中的 UID 无法通过名称服务解析，应检查 NIS、LDAP 或本地名称服务。',
      official_reference_url: 'https://docs.netapp.com/us-en/ontap-ems/secd-authsys-events.html',
      default_severity: 'error',
      version_scope: 'ONTAP 9.11.1–9.18.1',
      review_status: 'reviewed',
      is_active: true,
    },
    {
      id: 2,
      storage_type: 'netapp',
      event_code: 'nblade.execsOverLimit',
      association_type: 'performance_anomaly',
      title_zh: 'NFS 请求并发超过连接阈值',
      description_zh: '单个连接的并发在途请求超过允许值，客户端性能可能下降。',
      official_reference_url: 'https://docs.netapp.com/us-en/ontap-ems/nblade-execsoverlimit-events.html',
      default_severity: null,
      version_scope: 'ONTAP 9.10.1–9.18.1',
      review_status: 'reviewed',
      is_active: true,
    },
    {
      id: 3,
      storage_type: 'netapp',
      event_code: 'wafl.vol.blks_used.done',
      association_type: 'system_activity',
      title_zh: '已用块计算完成',
      description_zh: '卷或聚合的已用块扫描计算已结束，不表示故障。',
      official_reference_url: 'https://docs.netapp.com/us-en/ontap-ems-9181/wafl-vol-events.html',
      default_severity: 'info',
      version_scope: 'ONTAP 9.14.1、9.18.1',
      review_status: 'reviewed',
      is_active: true,
    },
    {
      id: 4,
      storage_type: 'isilon',
      event_code: '500010002',
      association_type: 'fault_log',
      title_zh: 'SmartQuotas 通知发送失败',
      description_zh: '系统未能向相关用户发送配额通知；不代表配额本身未生效。',
      official_reference_url: 'https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/',
      default_severity: null,
      version_scope: 'Dell PowerScale 官方事件列表；部署时按目标 OneFS 版本复核',
      review_status: 'reviewed',
      is_active: true,
    },
    {
      id: 5,
      storage_type: 'isilon',
      event_code: '500010001',
      association_type: 'capacity_threshold',
      title_zh: 'SmartQuotas 配额阈值触发',
      description_zh: 'SmartQuotas 域达到软限制、硬限制或宽限期相关阈值。',
      official_reference_url: 'https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/',
      default_severity: null,
      version_scope: 'Dell PowerScale 官方事件列表；部署时按目标 OneFS 版本复核',
      review_status: 'reviewed',
      is_active: true,
    },
    {
      id: 6,
      storage_type: 'isilon',
      event_code: 'SW_JOBENG_JOB_STATE',
      association_type: 'system_activity',
      title_zh: '作业状态变化（候选）',
      description_zh: '该符号代码仍需由目标阵列运行时事件目录复核。',
      official_reference_url: null,
      default_severity: null,
      version_scope: '目标 OneFS 运行时事件目录',
      review_status: 'pending',
      is_active: true,
    },
  ].map((item) => ({
    ...item,
    association_type_label: VENDOR_ASSOCIATION_LABELS[item.association_type],
    created_at: '2026-07-21T08:00:00Z',
    updated_at: '2026-07-21T08:00:00Z',
  }));
  const vendorSystemEvents = [
    {
      id: 901,
      storage_cluster_id: 1,
      source: 'netapp',
      severity: 'critical',
      event_code: 'secd.authsys.lookup.failed',
      fingerprint: 'netapp:secd.authsys.lookup.failed:node:node-a',
      association_type: 'fault_log',
      association_type_label: '故障日志',
      title_zh: 'UNIX 用户凭据查询失败',
      description_zh: '访问请求中的 UID 无法通过名称服务解析，应检查 NIS、LDAP 或本地名称服务。',
      review_status: 'reviewed',
      official_reference_url: 'https://docs.netapp.com/us-en/ontap-ems/secd-authsys-events.html',
      object_id: 'node-a',
      object_name: 'node-a',
      object_type: 'node',
      description: 'secd.authsys.lookup.failed: Unable to retrieve credentials for UID 1042 from configured name services.',
      occurred_at: '2026-07-21 09:06:21',
    },
    {
      id: 902,
      storage_cluster_id: 1,
      source: 'netapp',
      severity: 'warning',
      event_code: 'nblade.execsOverLimit',
      fingerprint: 'netapp:nblade.execsOverLimit:node:node-a',
      association_type: 'performance_anomaly',
      association_type_label: '性能异常',
      title_zh: 'NFS 请求并发超过连接阈值',
      description_zh: '单个连接的并发在途请求超过允许值，客户端性能可能下降。',
      review_status: 'reviewed',
      official_reference_url: 'https://docs.netapp.com/us-en/ontap-ems/nblade-execsoverlimit-events.html',
      object_id: 'node-a',
      object_name: 'node-a',
      object_type: 'node',
      description: 'nblade.execsOverLimit: In-flight NFS requests exceeded the connection limit.',
      occurred_at: '2026-07-21 08:58:10',
    },
    {
      id: 903,
      storage_cluster_id: 1,
      source: 'netapp',
      severity: 'warning',
      event_code: 'UNREVIEWED_VENDOR_CODE',
      fingerprint: 'netapp:UNREVIEWED_VENDOR_CODE:node:node-b',
      association_type: 'unknown',
      association_type_label: '未分类厂商事件',
      title_zh: '未收录的厂商事件代码',
      description_zh: '尚未在事件代码目录中确认该厂商事件的中文含义。',
      review_status: 'pending',
      official_reference_url: null,
      object_id: 'node-b',
      object_name: 'node-b',
      object_type: 'node',
      description: 'UNREVIEWED_VENDOR_CODE: Normalized vendor event awaiting catalog review.',
      occurred_at: '2026-07-21 08:50:00',
    },
    {
      id: 904,
      storage_cluster_id: 3,
      source: 'isilon',
      severity: 'error',
      event_code: '500010002',
      fingerprint: 'isilon:500010002:cluster:3',
      association_type: 'fault_log',
      association_type_label: '故障日志',
      title_zh: 'SmartQuotas 通知发送失败',
      description_zh: '系统未能向相关用户发送配额通知；不代表配额本身未生效。',
      review_status: 'reviewed',
      official_reference_url: 'https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/',
      object_id: 'cluster-3',
      object_name: 'PowerScale-研发',
      object_type: 'cluster',
      description: '500010002: SmartQuotas notification delivery failed for quota domain demo.',
      occurred_at: '2026-07-21 08:42:00',
    },
  ];

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
      withCapacity({ id: 1, asset_type: 'storage_usage', asset_id: '101', project_id: 1, effective_at: '2026-08-01T00:00:00Z', capacity_delta: 80, reason: 'Mock 演示容量计划', created_at: '2026-07-18T09:00:00Z' }),
      withCapacity({ id: 2, asset_type: 'group', asset_id: '11', project_id: 1, effective_at: '2026-08-15T00:00:00Z', capacity_delta: 150, reason: 'Mock 演示项目组扩容计划', created_at: '2026-07-18T09:30:00Z' }),
    ],
    capacityPredictionCandidates,
    conversations,
    vendorEventDefinitions,
    vendorSystemEvents,
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
const MOCK_OFFICIAL_REFERENCE_DOMAINS_BY_STORAGE_TYPE = {
  netapp: ['netapp.com'],
  isilon: ['dell.com', 'delltechnologies.com'],
};
function isValidMockOfficialReferenceUrl(value, storageType) {
  if (typeof value !== 'string' || !value || /\s/.test(value)) return false;
  try {
    const reference = new URL(value);
    const authority = value.match(/^https:\/\/([^/?#]+)/i)?.[1] || '';
    const hostname = reference.hostname.toLowerCase();
    return reference.protocol === 'https:'
      && (MOCK_OFFICIAL_REFERENCE_DOMAINS_BY_STORAGE_TYPE[storageType] || []).some(
        (domain) => hostname === domain || hostname.endsWith(`.${domain}`),
      )
      && !reference.username
      && !reference.password
      && !authority.includes(':')
      && !value.includes('@');
  } catch {
    return false;
  }
}
function validateMockVendorDefinition(item) {
  const reference = item?.official_reference_url;
  if (reference && !isValidMockOfficialReferenceUrl(reference, item.storage_type)) {
    throw error(422, '官方参考地址必须与存储类型匹配，使用 NetApp 或 Dell 官方 HTTPS 地址，且不能包含空格、认证信息、端口或 @ 字符');
  }
  if (item?.review_status !== 'reviewed') return;
  if (item.association_type === 'unknown' || !reference || !item.version_scope) {
    throw error(422, '已审核定义缺少明确分类、官方 HTTPS 参考地址或版本范围');
  }
}
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
    const records = {
      storage_cluster: state.clusters,
      project: state.projects,
      group: state.groups,
      storage_usage: state.usages,
    }[assetType] || [];
    const item = records.find((record) => record.id === Number(assetId));
    if (!item) throw error(404, '容量预测资源不存在');
    return item;
  };
  const capacityExhaustionRisk = (assetType, item) => ({
    asset_type: assetType,
    asset_id: String(item.id),
    level: 'watch',
    label: '关注',
    p50_exhaustion_at: null,
    p90_exhaustion_at: '2026-08-18T00:00:00Z',
    horizon_days: 30,
    reason: 'P90 预计在 30 日内达到硬限额',
    generated_at: '2026-07-22T00:00:00Z',
  });
  const capacityPrediction = (assetType, item) => withCapacity({
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
    curve: resourceTrend(item).map(([observed_at, p50]) => withCapacity({ observed_at, p10: Math.round(p50 * 0.95), p50, p90: Math.round(p50 * 1.05) })),
    data_unit: 'GB',
    exhaustion_dates: { p10: '2026-09-08', p50: '2026-09-22', p90: '2026-10-06' },
    algorithm_version: 'capacity-ai-v2',
    input_quality: { status: 'ready', coverage_ratio: 0.98, sample_count: 36, latest_observed_at: '2026-07-18T09:00:00Z', forecast_fresh_at: '2026-07-18T09:05:00Z', prediction_source: 'ai_candidate', candidate_version: 'capacity-ai-v2' },
    backtest_mape: 9.8,
    created_at: '2026-07-18T09:05:00Z',
  });
  const findResource = (path, suffix) => {
    const match = path.match(new RegExp(`^/(projects|groups|storage-usages|aggregates|volumes|qtrees|storage-clusters)/(\\d+)/${suffix}$`));
    if (!match) return null;
    const key = { projects: 'projects', groups: 'groups', 'storage-usages': 'usages', aggregates: 'aggregates', volumes: 'volumes', qtrees: 'qtrees', 'storage-clusters': 'clusters' }[match[1]];
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
    if (path === '/admin/vendor-event-definitions/discover' && verb === 'post') {
      const eventCode = 'UNREVIEWED_VENDOR_CODE';
      const existing = state.vendorEventDefinitions.some((item) => item.event_code === eventCode);
      if (!existing) {
        const id = Math.max(0, ...state.vendorEventDefinitions.map((item) => item.id)) + 1;
        state.vendorEventDefinitions.push({
          id,
          storage_type: 'netapp',
          event_code: eventCode,
          association_type: 'unknown',
          association_type_label: VENDOR_ASSOCIATION_LABELS.unknown,
          title_zh: '未收录的厂商事件代码',
          description_zh: '尚未在事件代码目录中确认该厂商事件的中文含义。',
          official_reference_url: null,
          default_severity: null,
          version_scope: null,
          review_status: 'pending',
          is_active: true,
          created_at: '2026-07-21T09:00:00Z',
          updated_at: '2026-07-21T09:00:00Z',
        });
      }
      return {
        created: existing ? 0 : 1,
        existing: state.vendorEventDefinitions.length - (existing ? 0 : 1),
        reconciled_incidents: 1,
      };
    }
    if (path === '/admin/vendor-event-definitions') {
      if (verb === 'post') {
        if (state.vendorEventDefinitions.some((item) => (
          item.storage_type === body?.storage_type && item.event_code === body?.event_code
        ))) throw error(409, '该存储类型和事件代码已存在');
        validateMockVendorDefinition(body);
        const now = '2026-07-21T09:00:00Z';
        const item = {
          ...(body || {}),
          id: Math.max(0, ...state.vendorEventDefinitions.map((record) => record.id)) + 1,
          association_type_label: VENDOR_ASSOCIATION_LABELS[body?.association_type]
            || VENDOR_ASSOCIATION_LABELS.unknown,
          created_at: now,
          updated_at: now,
        };
        state.vendorEventDefinitions.push(item);
        return item;
      }
      const filters = options.params || {};
      const keyword = String(filters.keyword || '').toLowerCase();
      const records = state.vendorEventDefinitions.filter((item) => {
        if (filters.storage_type && item.storage_type !== filters.storage_type) return false;
        if (filters.association_type && item.association_type !== filters.association_type) return false;
        if (filters.review_status && item.review_status !== filters.review_status) return false;
        if (keyword && !`${item.event_code} ${item.title_zh} ${item.description_zh}`.toLowerCase().includes(keyword)) return false;
        return true;
      });
      return page(records, filters);
    }
    const vendorDefinition = path.match(/^\/admin\/vendor-event-definitions\/(\d+)$/);
    if (vendorDefinition) {
      const item = state.vendorEventDefinitions.find(
        (record) => record.id === Number(vendorDefinition[1]),
      );
      if (!item) throw error(404, '厂商事件代码定义不存在');
      if (verb === 'delete') {
        state.vendorEventDefinitions.splice(state.vendorEventDefinitions.indexOf(item), 1);
        return {};
      }
      if (verb === 'patch') {
        validateMockVendorDefinition({ ...item, ...(body || {}) });
        Object.assign(item, body || {}, {
          association_type_label: VENDOR_ASSOCIATION_LABELS[body?.association_type || item.association_type]
            || VENDOR_ASSOCIATION_LABELS.unknown,
          updated_at: '2026-07-21T09:00:00Z',
        });
      }
      return item;
    }
    if (path === '/dashboard/summary') return {
      summary: withCapacity({ used_gb: 3210, limit_gb: 5200, available_gb: 1990, alert_count: state.alerts.length }),
      scope: { project_name: account.role === 'superadmin' ? '全局' : '芯片设计平台' },
    };
    if (path === '/dashboard/capacity-trend') return state.projects.map((project, index) => withCapacity({
      timestamp: `2026-07-${String(14 + index).padStart(2, '0')}`, used_gb: 2780 + index * 110,
    }));
    if (path === '/dashboard/capacity-items') return state.projects.map((project, index) => withCapacity({
      name: project.name, limit_gb: 600 + index * 100, used_gb: 360 + index * 75, available_gb: 240 + index * 25,
    }));
    if (path === '/dashboard/alert-levels') return [
      { name: '低', count: 5 }, { name: '中', count: 4 }, { name: '重要', count: 3 }, { name: '严重', count: 2 }, { name: '紧急', count: 1 },
    ];
    if (path === '/dashboard/top-users') return state.usages.map((usage) => withCapacity({ name: usage.rd_username, used_gb: usage.used }));
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
      const { storage_cluster_id: storageClusterId, status, category } = options.params || {};
      const records = scoped(account, state.incidents).filter((incident) => (
        (!storageClusterId || incident.storage_cluster_id === Number(storageClusterId))
        && (!status || incident.status === status)
        && (!category || incident.category === category)
      ));
      return page(records, options.params);
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
    const capacityPredictionResourcePath = path.match(/^\/v1\/capacity-predictions\/(storage_cluster|project|group|storage_usage)\/(\d+)(?:\/(risk|access|plans|related-incidents))?$/);
    if (capacityPredictionResourcePath) {
      const [, assetType, assetId, endpoint] = capacityPredictionResourcePath;
      const item = capacityPredictionResource(assetType, assetId);
      if (assetType === 'storage_cluster') {
        if (account.role !== 'superadmin') throw error(403);
      } else if (!allowed(account, item.project_id || item.id)) throw error(403);
      if (endpoint === 'risk') {
        if (!predictionVisibleTo(account)) throw error(403, '容量预测已停用');
        return capacityExhaustionRisk(assetType, item);
      }
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
          const plan = withCapacity({ id: state.capacityPredictionPlans.length + 1, asset_type: assetType, asset_id: String(assetId), project_id: item.project_id, effective_at: body?.effective_at, capacity_delta: body?.capacity_delta, reason: body?.reason, created_at: '2026-07-18T10:00:00Z' });
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
    if (realtimeItem) {
      const dataUnit = /^\/(aggregates|volumes|qtrees|projects|groups|storage-clusters)\//.test(path) ? 'TB' : 'GB';
      const quotaLimitGb = Number(realtimeItem.limit) || null;
      return {
        info: withCapacity(realtimeItem),
        data: resourceTrend(realtimeItem).map(([time, value]) => [time, dataUnit === 'TB' ? Math.round((value / 1024) * 10000) / 10000 : value]),
        data_unit: dataUnit,
        trend_meta: { indicator: 'used', quota_limit_gb: quotaLimitGb, quota_limit_tb: quotaLimitGb == null ? null : Math.round((quotaLimitGb / 1024) * 10000) / 10000 },
      };
    }
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
        info: withCapacity(volume),
        binding: { group_id: 1, group_name: '项目目录', project_id: 1, project_name: '演示项目', linux_path: '/proj/demo' },
        capacity: points.map(([time, value]) => [time, Math.round((value / 1024) * 10000) / 10000]),
        capacity_unit: 'TB',
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
        capacity_unit: 'TB',
        value_unit: valueType.includes('ratio') ? '%' : 'TB',
      });
      const groups = state.groups
        .filter((group) => group.project_id === projectId)
        .map((group) => ({
          ...storageNode(group, group.name, group.linux_path),
          children: state.usages
            .filter((usage) => usage.group_id === group.id)
            .map((usage) => storageNode(usage, usage.user?.rd_username || usage.rd_username || '', usage.linux_path)),
        }));
      return { data: groups, data_unit: 'TB' };
    }
    const projectMembers = path.match(/^\/projects\/(\d+)\/members(?:\/(\d+))?$/);
    if (projectMembers) {
      const members = state.memberships.filter((member) => member.project_id === Number(projectMembers[1]));
      if (projectMembers[2]) return members.find((member) => member.user_id === Number(projectMembers[2])) || {};
      return page(members);
    }
    if (path === '/aggregates/storage-trees') return { data: state.volumes, data_unit: 'TB' };
    const aggregateTree = path.match(/^\/aggregates\/(\d+)\/storage-tree$/);
    if (aggregateTree) return { data: state.volumes.filter((volume) => volume.aggregate_id === Number(aggregateTree[1])), data_unit: 'TB' };
    const systemEventDetail = path.match(/^\/storage-clusters\/(\d+)\/analytics\/system-events\/(\d+)$/);
    if (systemEventDetail) {
      const item = state.vendorSystemEvents.find((event) => (
        event.storage_cluster_id === Number(systemEventDetail[1])
        && event.id === Number(systemEventDetail[2])
      ));
      if (!item) throw error(404, '厂商系统事件不存在');
      const { storage_cluster_id: _clusterId, ...systemEventOut } = item;
      return systemEventOut;
    }
    const clusterAnalytics = path.match(/^\/storage-clusters\/(\d+)\/analytics\/(capacity-change|error-severity|top-latency|repeated-faults|system-events|export)$/);
    if (clusterAnalytics) {
      const [, clusterId, endpoint] = clusterAnalytics;
      const resources = Array.from({ length: 5 }, (_, index) => ({
        id: Number(clusterId) * 100 + index + 1,
        name: `vol_cluster_${clusterId}_${index + 1}`,
      }));
      if (endpoint === 'capacity-change') {
        const rawData = Array.from({ length: 6 }, (_, index) => ({ updated_at: `2026-07-${String(13 + index).padStart(2, '0')} 09:00:00`, used: 420 + index * 22 }));
        const startUsed = rawData[0].used;
        const endUsed = rawData.at(-1).used;
        const change = endUsed - startUsed;
        return {
          start_used: startUsed / 1024, end_used: endUsed / 1024, change: change / 1024,
          change_percent: Number(((change / startUsed) * 100).toFixed(2)), data_unit: 'TB',
          capacity: { start_used: capacityDisplay(startUsed), end_used: capacityDisplay(endUsed), change: capacityDisplay(change) },
          data: rawData.map((point) => ({ updated_at: point.updated_at, used: point.used / 1024, capacity: { used: capacityDisplay(point.used) } })),
        };
      }
      if (endpoint === 'error-severity') return { total: 5, counts: { critical: 1, error: 1, warning: 2, info: 1 }, sources: { netapp: 5 } };
      if (endpoint === 'top-latency') return { supported: true, data: resources.map((resource, index) => ({ object_id: resource.id, object_name: resource.name, p95_latency: 4 + index, avg_latency: 2 + index, max_latency: 8 + index, avg_read_latency: 1.5 + index, avg_write_latency: 2.5 + index, avg_iops: 800 + index * 120, avg_throughput: 1024 * 1024 * (index + 1) })) };
      if (endpoint === 'repeated-faults') {
        return {
          data: state.vendorSystemEvents
            .filter((event) => (
              event.storage_cluster_id === Number(clusterId)
              && event.review_status === 'reviewed'
              && event.association_type === 'fault_log'
            ))
            .map((event) => ({
              event_code: event.event_code,
              association_type: event.association_type,
              association_type_label: event.association_type_label,
              title_zh: event.title_zh,
              description_zh: event.description_zh,
              official_reference_url: event.official_reference_url || null,
              review_status: event.review_status,
              source: event.source,
              fingerprint: event.fingerprint,
              sample_event_id: event.id,
              count: 3,
              log_excerpt: event.description,
              first_occurred_at: '2026-07-21 08:06:21',
              last_occurred_at: event.occurred_at,
            })),
        };
      }
      if (endpoint === 'system-events') {
        const filters = options.params || {};
        const pageNumber = Math.max(1, Number(filters.page) || 1);
        const pageSize = Math.max(1, Number(filters.page_size) || 20);
        const keyword = String(filters.keyword || '').trim().toLowerCase();
        const records = state.vendorSystemEvents.filter((event) => {
          if (event.storage_cluster_id !== Number(clusterId)) return false;
          if (filters.fingerprint && event.fingerprint !== filters.fingerprint) return false;
          if (filters.event_code && !event.event_code.includes(filters.event_code)) return false;
          if (filters.severity && event.severity !== filters.severity) return false;
          if (keyword && ![
            event.event_code,
            event.object_id,
            event.object_name,
            event.description,
            event.title_zh,
            event.description_zh,
          ].filter(Boolean).join(' ').toLowerCase().includes(keyword)) return false;
          return true;
        });
        const offset = (pageNumber - 1) * pageSize;
        return {
          page: pageNumber,
          page_size: pageSize,
          total: records.length,
          data: records
            .slice(offset, offset + pageSize)
            .map(({ storage_cluster_id: _clusterId, ...systemEventOut }) => systemEventOut),
        };
      }
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
        const model = state.aiModels.find((record) => record.id === Number(body?.ai_model_id));
        const item = { id: state.capacityPredictionCandidates.length + 1, version: body?.version, ai_model_id: body?.ai_model_id, ai_model_name: model?.name || null, enabled: false, activation_ready: false, forecast_count: 0, fallback_count: 0, evaluations: [] };
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
