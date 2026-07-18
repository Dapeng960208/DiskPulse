const traceId = () => `mock-${Math.random().toString(36).slice(2, 10)}`;

export const DEMO_PASSWORD = 'Demo@2026';
export const DEMO_USERS = [
  { id: 1, username: 'demo-superadmin', commonName: '演示超级管理员', role: 'superadmin', projectIds: [1, 2] },
  { id: 2, username: 'demo-project-admin', commonName: '演示项目管理员', role: 'project_admin', projectIds: [1] },
  { id: 3, username: 'demo-editor', commonName: '演示编辑成员', role: 'editor', projectIds: [1] },
  { id: 4, username: 'demo-reader', commonName: '演示只读成员', role: 'reader', projectIds: [1] },
];

const seed = () => ({
  projects: [{ id: 1, name: '芯片设计平台', description: '虚构演示项目' }, { id: 2, name: '企业基础设施', description: '仅管理员可见' }],
  groups: [{ id: 11, name: 'EDA 研发组', project_id: 1, linux_path: '/data/eda', group_tag: { id: 1, name: '研发' }, storage_cluster: { id: 1, name: 'NetApp-演示', storage_type: 'netapp' }, capabilities: {} }],
  usages: [{ id: 101, name: 'eda-alice', rd_username: 'alice', project_id: 1, group_id: 11, linux_path: '/data/eda/alice', used: 320, limit: 500, use_ratio: 0.64, storage_cluster: { id: 1, name: 'NetApp-演示', storage_type: 'netapp' }, capabilities: {} }],
  incidents: [{ id: 301, project_id: 1, display_name: 'EDA 研发组容量', category: 'capacity_pressure', severity: 'warning', status: 'open', last_evidence_at: '2026-07-18 09:30:00' }],
  clusters: [{ id: 1, name: 'NetApp-演示', storage_type: 'netapp', protocol: 'https', enabled: true, status: 'healthy' }],
  aggregates: [{ id: 1, name: 'aggr_demo', storage_cluster_id: 1, used: 720, limit: 1000 }],
  volumes: [{ id: 1, name: 'vol_eda', storage_cluster_id: 1, used: 450, limit: 600 }],
  qtrees: [{ id: 1, name: 'qt_eda', volume_id: 1, storage_cluster_id: 1, used: 320, limit: 500 }],
  tags: [{ id: 1, name: '研发' }],
  alerts: [{ id: 1, project_id: 1, title: '容量使用率预警', level: 'warning', created_at: '2026-07-18 09:00:00' }],
  audits: [{ id: 1, action: 'project.member.read', result: 'success', project_id: 1, created_at: '2026-07-18 09:00:00' }],
  conversations: [{ id: 1, title: '容量分析', model_id: 1, messages: [] }],
});

function error(status, message = '没有权限') { const value = new Error(message); value.status = status; value.response = { status, data: { message } }; return value; }
function normalizePath(path) { const value = String(path || '').replace(/^https?:\/\/[^/]+/, '').replace(/^\/storage-pulse\/api/, '').split('?')[0]; return value.length > 1 ? value.replace(/\/$/, '') : value; }
function page(content) { return { content, total: content.length, totalElements: content.length, data: content, meta: { total: content.length }, traceId: traceId() }; }

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
  const capabilities = (account, projectId) => {
    const scoped = allowed(account, projectId);
    const projectAdmin = scoped && account.role === 'project_admin';
    return { edit: scoped && ['superadmin', 'project_admin', 'editor'].includes(account.role), manage_members: projectAdmin || account.role === 'superadmin', manage_project_admins: account.role === 'superadmin', view_audit_events: projectAdmin || account.role === 'superadmin', adjust_quota: projectAdmin || account.role === 'superadmin' };
  };
  const scoped = (account, records) => account.role === 'superadmin' ? records : records.filter((record) => allowed(account, record.project_id || 1));
  const request = async (method, rawPath, body, token, options = {}) => {
    const path = normalizePath(rawPath); const verb = method.toLowerCase();
    if (path === '/users/login' && verb === 'post') {
      const account = DEMO_USERS.find((item) => item.username === body?.username);
      if (!account || body?.password !== DEMO_PASSWORD) throw error(401, '用户名或密码错误');
      const value = `mock:${account.username}`; tokens.set(value, account.username); return { result: { token: value }, token: value, data: { token: value }, meta: {}, traceId: traceId() };
    }
    const account = accountFor(token); if (!account) throw error(401, '请先登录');
    if (path === '/users/current/profile') return { result: profile(account), ...profile(account), meta: {}, traceId: traceId() };
    if (path.startsWith('/admin') && account.role !== 'superadmin') throw error(403);
    if (path === '/dashboard/capacity-trend') return page([
      { date: '2026-07-14', used: 580, limit: 1000 }, { date: '2026-07-15', used: 610, limit: 1000 }, { date: '2026-07-16', used: 645, limit: 1000 }, { date: '2026-07-17', used: 680, limit: 1000 }, { date: '2026-07-18', used: 720, limit: 1000 },
    ]);
    if (path === '/dashboard/capacity-items') return page([{ name: 'EDA 研发组', used: 320, limit: 500 }, { name: '验证平台', used: 230, limit: 300 }, { name: '基础服务', used: 170, limit: 200 }]);
    if (path === '/dashboard/alert-levels') return page([{ name: 'warning', value: 4 }, { name: 'critical', value: 1 }]);
    if (path === '/dashboard/top-users') return page([{ name: 'alice', used: 180 }, { name: 'bob', used: 140 }, { name: 'carol', used: 95 }]);
    if (path === '/v1/incidents') {
      const records = scoped(account, state.incidents);
      return page(records);
    }
    const incident = path.match(/^\/v1\/incidents\/(\d+)/);
    if (incident) { const item = state.incidents.find((record) => record.id === Number(incident[1])); if (!item || !allowed(account, item.project_id)) throw error(403); if (verb === 'patch' && !capabilities(account, item.project_id).edit) throw error(403); Object.assign(item, body || {}); return item; }
    const projectMatch = path.match(/^\/projects\/(\d+)/);
    if (projectMatch) { const item = state.projects.find((record) => record.id === Number(projectMatch[1])); if (!item || !allowed(account, item.id)) throw error(403); return { ...item, capabilities: capabilities(account, item.id) }; }
    if (path === '/projects') return page(scoped(account, state.projects.map((item) => ({ ...item, project_id: item.id, capabilities: capabilities(account, item.id) }))));
    const tableMap = { '/groups': 'groups', '/storage-usages': 'usages', '/storage-clusters': 'clusters', '/aggregates': 'aggregates', '/volumes': 'volumes', '/qtrees': 'qtrees', '/group-tags': 'tags', '/alerts': 'alerts', '/v1/audit-events': 'audits', '/storage-back-up-records': 'usages', '/users': 'usages' };
    if (path === '/storage-usages/export' && options.responseType === 'blob') return new Blob(['Linux路径,已用容量\n/data/eda/alice,320'], { type: 'text/csv' });
    if (tableMap[path]) {
      const records = state[tableMap[path]];
      if (verb === 'post') { if (account.role === 'reader') throw error(403); const item = { id: Math.max(0, ...records.map((record) => record.id || 0)) + 1, project_id: body?.project_id || 1, ...(body || {}), capabilities: capabilities(account, body?.project_id || 1) }; records.push(item); return item; }
      return page(scoped(account, records.map((item) => ({ ...item, capabilities: { ...item.capabilities, ...capabilities(account, item.project_id || 1) } }))));
    }
    const resource = Object.entries(tableMap).find(([prefix]) => path.startsWith(`${prefix}/`));
    if (resource) {
      const [, key] = resource; const id = Number(path.slice(resource[0].length + 1)); const records = state[key]; const item = records.find((record) => record.id === id);
      if (!item || !allowed(account, item.project_id || 1)) throw error(403);
      if (verb === 'patch' || verb === 'put') { if (account.role === 'reader') throw error(403); Object.assign(item, body || {}); return item; }
      if (verb === 'delete') { if (account.role === 'reader') throw error(403); records.splice(records.indexOf(item), 1); return {}; }
      return { ...item, capabilities: { ...item.capabilities, ...capabilities(account, item.project_id || 1) } };
    }
    if (path.includes('dashboard')) return { summary: { used_gb: 720, limit_gb: 1000, available_gb: 280 }, scope: { project_name: account.role === 'superadmin' ? '全局' : '芯片设计平台' }, content: [], data: [], meta: {}, traceId: traceId() };
    if (path.startsWith('/ai/')) return path.includes('conversations') ? page(state.conversations) : [];
    if (path.includes('export') && options.responseType === 'blob') return new Blob(['DiskPulse Mock export']);
    return page([{ id: 1, name: 'Mock 演示数据', project_id: 1, status: 'healthy', capabilities: capabilities(account, 1) }]);
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
    data: result instanceof Blob || result?.result ? result : { result, meta: result?.meta || {}, traceId: result?.traceId || traceId() },
    status: 200,
    statusText: 'OK',
    headers: { 'x-trace-id': result.traceId || traceId() },
    config,
  }));
}
