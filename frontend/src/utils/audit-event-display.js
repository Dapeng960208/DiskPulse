const actionLabels = {
  'storage.collection.run': '存储采集',
};

const actorTypeLabels = {
  ai_tool: 'AI 工具',
  service: '系统定时任务',
  system: '系统服务',
  user: '人工用户',
};

const phaseLabels = {
  attempt: '开始执行',
  result: '执行结果',
};

const summaryLabels = {
  group_count: '更新项目组',
  method: '请求方式',
  status_code: '响应状态',
  storage_usage_count: '更新用户目录',
};

function displayName(actor) {
  return actor?.display_name || actor?.common_name || actor?.commonName || actor?.rd_username || actor?.username || '';
}

function pad(value) {
  return String(value).padStart(2, '0');
}

export function formatAuditOccurredAt(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

export function auditRequesterLabel(event = {}) {
  const name = displayName(event.actor);
  if (name) return name;
  if (event.actor_user_id != null) return `用户 #${event.actor_user_id}`;
  return {
    ai_tool: 'AI 工具',
    service: '系统定时任务',
    system: '系统服务',
  }[event.actor_type] || '未记录';
}

export function auditActorTypeLabel(actorType) {
  return actorTypeLabels[actorType] || actorType || '未记录';
}

export function auditActionLabel(action) {
  return actionLabels[action] || action || '未记录';
}

export function auditActionDescription(action) {
  const label = auditActionLabel(action);
  return label === action ? label : `${label}（${action}）`;
}

export function auditPhaseLabel(phase) {
  return phaseLabels[phase] || phase || '未记录';
}

export function auditOutcomeLabel(outcome) {
  return { denied: '已拒绝', failure: '失败', success: '成功' }[outcome] || outcome || '未记录';
}

export function auditSummaryEntries(value) {
  if (value == null || typeof value !== 'object' || Array.isArray(value)) return [];
  return Object.entries(value)
    .filter(([, entry]) => entry !== null && entry !== undefined && entry !== '')
    .map(([key, entry]) => ({
      label: summaryLabels[key] || key,
      value: typeof entry === 'string' ? entry : JSON.stringify(entry),
    }));
}

export function hasAuditValue(value) {
  if (value == null || value === '') return false;
  if (Array.isArray(value)) return value.length > 0;
  return typeof value !== 'object' || Object.keys(value).length > 0;
}
