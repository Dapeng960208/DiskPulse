import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  DEMO_PASSWORD,
  DEMO_USERS,
  createMockGateway,
  mockAxiosAdapter,
} from '@/mocks/runtime.js';

describe('frontend mock runtime', () => {
  it('exposes pnpm mock through a Vite mode that enables the mock runtime', () => {
    // Review source: enabling Mock required manually setting VITE_USE_MOCKS.
    // Resolution contract: `pnpm mock` selects a committed mock mode whose
    // environment enables the in-memory gateway without extra shell syntax.
    const frontendRoot = resolve(import.meta.dirname, '../..');
    const packageJson = JSON.parse(readFileSync(resolve(frontendRoot, 'package.json'), 'utf8'));
    const mockEnvironment = readFileSync(resolve(frontendRoot, '.env.mock'), 'utf8');

    expect(packageJson.scripts.mock).toBe('vite --host --mode mock');
    expect(mockEnvironment).toMatch(/^VITE_USE_MOCKS=true$/m);
  });

  it('authenticates each documented demo account and returns its profile', async () => {
    const gateway = createMockGateway();

    for (const account of DEMO_USERS) {
      const login = await gateway.request('post', '/users/login', {
        username: account.username,
        password: DEMO_PASSWORD,
      });
      const profile = await gateway.request('get', '/users/current/profile', undefined, login.token);

      expect(profile.roleCodes).toContain(account.role);
    }
  });

  it('filters project resources and capabilities by the signed-in role', async () => {
    const gateway = createMockGateway();
    const reader = await gateway.login('demo-reader', DEMO_PASSWORD);
    const editor = await gateway.login('demo-editor', DEMO_PASSWORD);
    const admin = await gateway.login('demo-project-admin', DEMO_PASSWORD);

    await expect(gateway.request('get', '/projects/2', undefined, reader.token)).rejects.toMatchObject({ status: 403 });
    expect((await gateway.request('get', '/projects/1', undefined, reader.token)).capabilities).toMatchObject({ edit: false, manage_members: false });
    expect((await gateway.request('get', '/projects/1', undefined, editor.token)).capabilities.edit).toBe(true);
    expect((await gateway.request('get', '/projects/1', undefined, admin.token)).capabilities).toMatchObject({ manage_members: true, view_audit_events: true });
  });

  it('scopes project and user-detail related datasets by their explicit identifiers', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);
    const projectAdmin = await gateway.login('demo-project-admin', DEMO_PASSWORD);
    const reader = await gateway.login('demo-reader', DEMO_PASSWORD);

    const usages = await gateway.request('get', '/storage-usages', undefined, superadmin.token, {
      params: { project_id: 1 },
    });
    const alerts = await gateway.request('get', '/storage-alerts', undefined, superadmin.token, {
      params: { related_type: 'StorageUsage', related_id: 101 },
    });
    const forecasts = await gateway.request('get', '/v1/capacity-predictions', undefined, superadmin.token, {
      params: { page: 1, size: 20 },
    });
    const quotaHistory = await gateway.request('get', '/storage-usages/101/quota/history', undefined, superadmin.token);
    const projectAdminUsage = await gateway.request('get', '/storage-usages/101', undefined, projectAdmin.token);

    expect(usages.content).toHaveLength(1);
    expect(usages.content[0].project_id).toBe(1);
    expect(alerts.content).toHaveLength(1);
    expect(alerts.content[0]).toMatchObject({ related_type: 'StorageUsage', related_id: 101 });
    expect(forecasts.content[0]).toMatchObject({ asset_type: 'storage_usage', asset_id: '101' });
    expect(quotaHistory[0]).toMatchObject({
      action: 'quota.adjust',
      before_summary: { hard_limit: expect.any(Number) },
      after_summary: { hard_limit: expect.any(Number) },
    });
    expect(projectAdminUsage.capabilities.adjust_quota).toBe(false);
    await expect(gateway.request('get', '/storage-usages/101/quota/history', undefined, projectAdmin.token))
      .rejects.toMatchObject({ status: 403 });
    await expect(gateway.request('get', '/storage-usages/101/quota/history', undefined, reader.token))
      .rejects.toMatchObject({ status: 403 });
  });

  it('returns current storage distribution as a project-group to user tree', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const tree = await gateway.request('get', '/projects/1/storage-tree', undefined, superadmin.token, {
      params: { value_type: 'used' },
    });

    expect(tree.data).toHaveLength(1);
    expect(tree.data[0]).toMatchObject({
      name: expect.any(String),
      value: expect.any(Number),
      used: expect.any(Number),
      children: [{
        name: expect.any(String),
        value: expect.any(Number),
        used: expect.any(Number),
      }],
    });
  });

  it('keeps system resource reads and writes exclusive to the superadmin', async () => {
    // Review source: the generic Mock table map exposed system inventory to
    // project-scoped roles. Resolution contract: mirror real route RBAC while
    // leaving project resources on their existing capability checks.
    const gateway = createMockGateway();
    const projectAdmin = await gateway.login('demo-project-admin', DEMO_PASSWORD);
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);
    const systemPaths = [
      '/storage-clusters',
      '/aggregates',
      '/volumes',
      '/qtrees',
      '/group-tags',
      '/users',
      '/storage-back-up-records',
      '/admin/vendor-event-definitions',
    ];

    for (const path of systemPaths) {
      await expect(gateway.request('get', path, undefined, projectAdmin.token))
        .rejects.toMatchObject({ status: 403 });
      await expect(gateway.request('post', path, { name: 'blocked' }, projectAdmin.token))
        .rejects.toMatchObject({ status: 403 });
      await expect(gateway.request('get', path, undefined, superadmin.token))
        .resolves.toMatchObject({ content: expect.any(Array) });
    }

    await expect(gateway.request('get', '/groups', undefined, projectAdmin.token))
      .resolves.toMatchObject({ content: expect.any(Array) });
  });

  it('keeps permitted writes in memory and exposes export and AI stream responses', async () => {
    const gateway = createMockGateway();
    const editor = await gateway.login('demo-editor', DEMO_PASSWORD);
    const initial = await gateway.request('get', '/v1/incidents', undefined, editor.token);
    const updated = await gateway.request('patch', `/v1/incidents/${initial.content[0].id}`, { status: 'acknowledged' }, editor.token);
    const exported = await gateway.request('get', '/storage-usages/export', undefined, editor.token, { responseType: 'blob' });
    const events = await gateway.streamAiMessage(editor.token, 1, '查看容量');

    expect(updated.status).toBe('acknowledged');
    expect(exported).toBeInstanceOf(Blob);
    expect(events.map((event) => event.event)).toContain('completed');
  });

  it('filters associated incidents by cluster, status, and category before pagination', async () => {
    const gateway = createMockGateway();
    const admin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const response = await gateway.request('get', '/v1/incidents', undefined, admin.token, {
      params: {
        storage_cluster_id: 1,
        status: 'acknowledged',
        category: 'device_fault',
        page: 1,
        size: 20,
      },
    });

    expect(response).toMatchObject({ total: 1 });
    expect(response.content).toEqual([
      expect.objectContaining({ status: 'acknowledged', category: 'device_fault' }),
    ]);
  });

  it('returns complete incident detail mock data for the incident drawer', async () => {
    const gateway = createMockGateway();
    const admin = await gateway.login('demo-superadmin', DEMO_PASSWORD);
    const detail = await gateway.request('get', '/v1/incidents/301', undefined, admin.token);

    expect(detail).toMatchObject({
      id: 301,
      capabilities: { edit: true, create_maintenance_window: true },
      diagnosis: { confidence: expect.any(String), candidates: expect.any(Array) },
    });
    expect(detail.evidence).toHaveLength(2);
    expect(detail.evidence[0]).toMatchObject({
      evidence_type: expect.any(String),
      source: expect.any(String),
      source_ref: expect.any(String),
      observed_at: expect.any(String),
    });
    expect(detail.timeline).toHaveLength(2);
    expect(detail.timeline[0]).toMatchObject({
      event_type: expect.any(String),
      occurred_at: expect.any(String),
    });
  });

  it('serves chart datasets and complete CRUD for every seeded table', async () => {
    const gateway = createMockGateway();
    const admin = await gateway.login('demo-superadmin', DEMO_PASSWORD);
    const trend = await gateway.request('get', '/dashboard/capacity-trend', undefined, admin.token);
    const created = await gateway.request('post', '/group-tags', { name: 'Mock 新标签' }, admin.token);
    const updated = await gateway.request('patch', `/group-tags/${created.id}`, { name: 'Mock 已更新标签' }, admin.token);
    await gateway.request('delete', `/group-tags/${created.id}`, undefined, admin.token);
    const tags = await gateway.request('get', '/group-tags', undefined, admin.token);

    expect(trend.length).toBeGreaterThan(1);
    expect(updated.name).toBe('Mock 已更新标签');
    expect(tags.content.some((tag) => tag.id === created.id)).toBe(false);
  });

  it('supplies candidate models and completed evaluation windows for capacity prediction governance', async () => {
    const gateway = createMockGateway();
    const admin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const settings = await gateway.request('get', '/v1/admin/capacity-prediction-settings', undefined, admin.token);
    const candidates = await gateway.request('get', '/v1/admin/capacity-prediction-candidates', undefined, admin.token);

    expect(settings.visible).toBe(true);
    expect(candidates).toHaveLength(2);
    expect(candidates[0]).toMatchObject({
      version: 'capacity-ai-v2',
      ai_model_id: 1,
      activation_ready: true,
    });
    expect(candidates[0].evaluations).toHaveLength(3);
  });

  it('paginates capacity prediction lists after applying project scope', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);
    const projectAdmin = await gateway.login('demo-project-admin', DEMO_PASSWORD);

    const finalFirstPage = await gateway.request('get', '/v1/capacity-predictions', undefined, superadmin.token, {
      params: { page: 1, size: 3 },
    });
    const finalSecondPage = await gateway.request('get', '/v1/capacity-predictions', undefined, superadmin.token, {
      params: { page: 2, size: 3 },
    });
    const scopedSecondPage = await gateway.request('get', '/v1/capacity-predictions', undefined, projectAdmin.token, {
      params: { page: 2, size: 1 },
    });
    const baselineFirstPage = await gateway.request('get', '/v1/forecasts', undefined, superadmin.token, {
      params: { page: 1, size: 4 },
    });
    const baselineSecondPage = await gateway.request('get', '/v1/forecasts', undefined, superadmin.token, {
      params: { page: 2, size: 4 },
    });
    const scopedBaselineSecondPage = await gateway.request('get', '/v1/forecasts', undefined, projectAdmin.token, {
      params: { page: 2, size: 1 },
    });

    expect(finalFirstPage).toMatchObject({ total: 10, totalElements: 10, meta: { total: 10 } });
    expect(finalFirstPage.content).toHaveLength(3);
    expect(finalSecondPage.content).toHaveLength(3);
    expect(finalSecondPage.data).toEqual(finalSecondPage.content);
    expect(finalSecondPage.content.map((item) => item.id))
      .not.toEqual(finalFirstPage.content.map((item) => item.id));
    expect(scopedSecondPage).toMatchObject({ total: 2, totalElements: 2, meta: { total: 2 } });
    expect(scopedSecondPage.content).toHaveLength(1);
    expect(baselineFirstPage).toMatchObject({ total: 25, totalElements: 25, meta: { total: 25 } });
    expect(baselineFirstPage.content).toHaveLength(4);
    expect(baselineSecondPage.content).toHaveLength(4);
    expect(baselineSecondPage.content.map((item) => item.id))
      .not.toEqual(baselineFirstPage.content.map((item) => item.id));
    expect(scopedBaselineSecondPage)
      .toMatchObject({ content: [expect.any(Object)], total: 2, totalElements: 2, meta: { total: 2 } });
  });

  it('keeps capacity predictions available to superadmins when user visibility is disabled', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);
    const reader = await gateway.login('demo-reader', DEMO_PASSWORD);

    await gateway.request(
      'patch',
      '/v1/admin/capacity-prediction-settings',
      { user_visible: false },
      superadmin.token,
    );

    await expect(gateway.request('get', '/v1/capacity-predictions/visibility', undefined, superadmin.token))
      .resolves.toEqual({ visible: true });
    await expect(gateway.request('get', '/v1/capacity-predictions', undefined, superadmin.token, {
      params: { page: 1, size: 1 },
    })).resolves.toMatchObject({ content: expect.any(Array), total: 10 });
    await expect(gateway.request('get', '/v1/capacity-predictions/storage_usage/101', undefined, superadmin.token))
      .resolves.toMatchObject({ asset_type: 'storage_usage', asset_id: '101' });
    await expect(gateway.request('get', '/v1/capacity-predictions/visibility', undefined, reader.token))
      .resolves.toEqual({ visible: false });
    await expect(gateway.request('get', '/v1/capacity-predictions', undefined, reader.token))
      .rejects.toMatchObject({ status: 403 });
    await expect(gateway.request('get', '/v1/capacity-predictions/storage_usage/101', undefined, reader.token))
      .rejects.toMatchObject({ status: 403 });
    await expect(gateway.request(
      'get',
      '/v1/capacity-predictions/storage_usage/101/related-incidents',
      undefined,
      reader.token,
    )).resolves.toEqual(expect.any(Array));
    await expect(gateway.request(
      'get',
      '/v1/capacity-predictions/storage_usage/102/related-incidents',
      undefined,
      reader.token,
    )).rejects.toMatchObject({ status: 403 });

    await gateway.request(
      'patch',
      '/v1/admin/capacity-prediction-settings',
      { user_visible: true },
      superadmin.token,
    );
    await expect(gateway.request('get', '/v1/capacity-predictions/visibility', undefined, reader.token))
      .resolves.toEqual({ visible: true });
    await expect(gateway.request('get', '/v1/capacity-predictions', undefined, reader.token))
      .resolves.toMatchObject({ total: 2 });
  });

  it('gives the superadmin five or more records for every visible mock data source', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);
    const listPaths = [
      '/projects',
      '/groups',
      '/storage-usages',
      '/storage-alerts',
      '/v1/incidents',
      '/storage-clusters',
      '/aggregates',
      '/volumes',
      '/qtrees',
      '/group-tags',
      '/users',
      '/storage-back-up-records',
      '/v1/audit-events',
      '/ai/models',
      '/ai/conversations',
      '/admin/ai-models',
      '/admin/ai-audits',
    ];
    const dashboardPaths = [
      '/dashboard/capacity-trend',
      '/dashboard/capacity-items',
      '/dashboard/alert-levels',
      '/dashboard/top-users',
    ];

    for (const path of listPaths.filter((path) => path !== '/ai/conversations')) {
      const response = await gateway.request('get', path, undefined, superadmin.token);
      const content = response.content ?? response;
      expect(content, path).toEqual(expect.any(Array));
      expect(content.length, path).toBeGreaterThanOrEqual(5);
    }

    const conversations = await gateway.request('get', '/ai/conversations', undefined, superadmin.token);
    expect(conversations).toEqual(expect.any(Array));
    expect(conversations).toHaveLength(5);
    for (const path of dashboardPaths) {
      const response = await gateway.request('get', path, undefined, superadmin.token);
      const content = response.content ?? response;
      expect(content.length, path).toBeGreaterThanOrEqual(5);
    }

    const summary = await gateway.request('get', '/dashboard/summary', undefined, superadmin.token);
    const configuration = await gateway.request('get', '/config/storage', undefined, superadmin.token);
    const conversation = await gateway.request('get', '/ai/conversations/1', undefined, superadmin.token);
    const latency = await gateway.request('get', '/storage-clusters/1/analytics/top-latency', undefined, superadmin.token);

    expect(summary.summary.alert_count).toBeGreaterThanOrEqual(5);
    expect(configuration.storage_alert_rule).toMatchObject({
      quota_basis: 'hard',
      important: { threshold: expect.any(Number), repeat_hours: expect.any(Number) },
      serious: { threshold: expect.any(Number), repeat_hours: expect.any(Number) },
      emergency: { threshold: expect.any(Number), repeat_hours: expect.any(Number) },
    });
    expect(conversation.messages.length).toBeGreaterThanOrEqual(5);
    expect(latency.data).toHaveLength(5);
  });

  it('passes mock list payloads to API clients without an extra result wrapper', async () => {
    const login = await createMockGateway().login('demo-superadmin', DEMO_PASSWORD);
    const response = await mockAxiosAdapter({
      method: 'get',
      url: '/projects',
      headers: { Authorization: `Bearer ${login.token}` },
    });

    expect(response.data.content).toHaveLength(5);
  });

  it('supports the vendor event definition admin lifecycle with reviewed evidence', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const listed = await gateway.request(
      'get',
      '/admin/vendor-event-definitions',
      undefined,
      superadmin.token,
      { params: { page: 1, size: 20, review_status: 'reviewed' } },
    );
    expect(listed.content[0]).toMatchObject({
      event_code: expect.any(String),
      association_type: expect.not.stringMatching(/^unknown$/),
      official_reference_url: expect.stringMatching(/^https:\/\//),
      version_scope: expect.any(String),
      review_status: 'reviewed',
      recommended_solution_zh: expect.any(String),
    });

    const created = await gateway.request(
      'post',
      '/admin/vendor-event-definitions',
      {
        storage_type: 'netapp',
        event_code: 'mock.test.event',
        association_type: 'unknown',
        title_zh: '待审核演示事件',
        description_zh: '仅用于前端演示。',
        official_reference_url: null,
        default_severity: null,
        version_scope: null,
        review_status: 'pending',
        recommended_solution_zh: null,
        is_active: true,
      },
      superadmin.token,
    );
    expect(created).toMatchObject({ event_code: 'mock.test.event', review_status: 'pending' });

    await expect(gateway.request(
      'patch',
      `/admin/vendor-event-definitions/${created.id}`,
      {
        association_type: 'fault_log',
        official_reference_url: 'https://docs.netapp.com/us-en/ontap-ems/test-events.html',
        version_scope: 'ONTAP test fixture',
        review_status: 'reviewed',
        recommended_solution_zh: null,
      },
      superadmin.token,
    )).rejects.toMatchObject({ status: 422 });

    const updated = await gateway.request(
      'patch',
      `/admin/vendor-event-definitions/${created.id}`,
      { title_zh: '已更新的待审核演示事件' },
      superadmin.token,
    );
    expect(updated.title_zh).toBe('已更新的待审核演示事件');

    await gateway.request(
      'delete',
      `/admin/vendor-event-definitions/${created.id}`,
      undefined,
      superadmin.token,
    );
    const afterDelete = await gateway.request(
      'get',
      '/admin/vendor-event-definitions',
      undefined,
      superadmin.token,
      { params: { keyword: 'mock.test.event' } },
    );
    expect(afterDelete.total).toBe(0);
  });

  it.each([
    'http://docs.netapp.com/us-en/ontap-ems/events.html',
    'https://docs.example.com/vendor-events',
    'https://evilnetapp.com/vendor-events',
    'https://operator@docs.netapp.com/us-en/ontap-ems/events.html',
    'https://docs.netapp.com:443/us-en/ontap-ems/events.html',
    'https://docs.netapp.com./us-en/ontap-ems/events.html',
    'https://docs.netapp.com/us-en/ontap-ems/events@v1.html',
    'https://www.dell.com/support/manuals/en-us/powerscale-onefs/events',
    ' https://docs.netapp.com/us-en/ontap-ems/events.html',
  ])('rejects an unsafe non-empty official URL for a pending mock definition: %s', async (officialReferenceUrl) => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    await expect(gateway.request(
      'post',
      '/admin/vendor-event-definitions',
      {
        storage_type: 'netapp',
        event_code: 'mock.pending.reference',
        association_type: 'unknown',
        title_zh: '待审核参考地址',
        description_zh: '验证待审核定义也不能保存非官方或不安全链接。',
        official_reference_url: officialReferenceUrl,
        default_severity: null,
        version_scope: null,
        review_status: 'pending',
        is_active: true,
      },
      superadmin.token,
    )).rejects.toMatchObject({ status: 422 });
  });

  it.each([
    'https://www.dell.com/support/manuals/en-us/powerscale-onefs/events',
    'https://infohub.delltechnologies.com/en-us/l/powerscale-onefs/events/',
  ])('accepts an official vendor subdomain in mock definitions: %s', async (officialReferenceUrl) => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    await expect(gateway.request(
      'post',
      '/admin/vendor-event-definitions',
      {
        storage_type: 'isilon',
        event_code: 'mock.dell.reference',
        association_type: 'unknown',
        title_zh: 'Dell 官方参考地址',
        description_zh: '验证 Dell 官方子域名可以保存。',
        official_reference_url: officialReferenceUrl,
        default_severity: null,
        version_scope: null,
        review_status: 'pending',
        is_active: true,
      },
      superadmin.token,
    )).resolves.toMatchObject({ event_code: 'mock.dell.reference' });
  });

  it('returns classified system events and a clickable normalized log detail', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const events = await gateway.request(
      'get',
      '/storage-clusters/1/analytics/system-events',
      undefined,
      superadmin.token,
      { params: { page: 1, page_size: 20 } },
    );
    expect(events.data[0]).toMatchObject({
      id: expect.any(Number),
      event_code: expect.any(String),
      association_type: 'fault_log',
      association_type_label: '故障日志',
      title_zh: expect.any(String),
      review_status: 'reviewed',
      recommended_solution_zh: expect.any(String),
      fingerprint: expect.any(String),
      description: expect.any(String),
    });

    const detail = await gateway.request(
      'get',
      `/storage-clusters/1/analytics/system-events/${events.data[0].id}`,
      undefined,
      superadmin.token,
    );
    expect(detail.description).toContain('secd.authsys.lookup.failed');
    expect(detail.recommended_solution_zh).toEqual(expect.any(String));
    expect(detail).not.toHaveProperty('related_info');
    expect(JSON.stringify(detail)).not.toContain('raw');
  });

  it('filters mock system events by keyword and returns repeated-fault occurrence windows', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const filtered = await gateway.request(
      'get',
      '/storage-clusters/1/analytics/system-events',
      undefined,
      superadmin.token,
      { params: { keyword: 'EXECSOVERLIMIT', page: 1, page_size: 20 } },
    );
    expect(filtered).toMatchObject({ total: 1, data: [{ id: 902 }] });

    const repeated = await gateway.request(
      'get',
      '/storage-clusters/1/analytics/repeated-faults',
      undefined,
      superadmin.token,
    );
    expect(repeated.data[0]).toMatchObject({
      first_occurred_at: expect.any(String),
      last_occurred_at: expect.any(String),
    });
  });

  it('supplies every usage-list display field and flat quota thresholds', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const usages = await gateway.request('get', '/storage-usages', undefined, superadmin.token);
    const thresholds = await gateway.request('get', '/config/storage-alert-thresholds', undefined, superadmin.token);

    expect(usages.content[0]).toMatchObject({
      project: { id: expect.any(Number), name: expect.any(String) },
      group_tag: { id: expect.any(Number), name: expect.any(String) },
      group: { id: expect.any(Number), name: expect.any(String) },
      storage_cluster: { id: expect.any(Number), name: expect.any(String) },
      limit: expect.any(Number),
      soft_limit: expect.any(Number),
      used: expect.any(Number),
      use_ratio: 40,
      soft_use_ratio: 45,
    });
    expect(thresholds).toEqual({ important: 80, serious: 90, emergency: 95 });
  });

  it('supplies every project-list display field', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const projects = await gateway.request('get', '/projects', undefined, superadmin.token);

    expect(projects.content[0]).toMatchObject({
      storage_clusters: [{ id: expect.any(Number), name: expect.any(String), storage_type: expect.any(String) }],
      in_charge_user: { id: expect.any(Number), rd_username: expect.any(String) },
      limit: expect.any(Number),
      used: expect.any(Number),
      use_ratio: expect.any(Number),
    });
  });

  it('supplies readable AI audit display summaries', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const audits = await gateway.request('get', '/admin/ai-audits', undefined, superadmin.token);

    expect(audits.content[0]).toMatchObject({
      conversation: { title: expect.any(String) },
      user: { rd_username: expect.any(String) },
      model: { name: expect.any(String) },
      tool_names: [expect.any(String)],
    });
  });

  it('supplies a scheduled storage-collection audit with a source and result summary', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const audits = await gateway.request('get', '/v1/audit-events', undefined, superadmin.token);
    const collection = audits.content.find((item) => item.action === 'storage.collection.run');

    expect(collection).toMatchObject({
      actor_type: 'service',
      resource: { type: 'storage_cluster', name: expect.any(String) },
      phase: 'result',
      after_summary: { storage_usage_count: expect.any(Number), group_count: expect.any(Number) },
    });
  });

  it('mirrors explicit capacity units and TB realtime series from the backend contract', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);
    const [volumes, realtime, monitoring, clusterCapacity, dashboard, forecast] = await Promise.all([
      gateway.request('get', '/volumes', undefined, superadmin.token),
      gateway.request('get', '/volumes/1/realtime', undefined, superadmin.token),
      gateway.request('get', '/volumes/1/monitoring', undefined, superadmin.token),
      gateway.request('get', '/storage-clusters/1/analytics/capacity-change', undefined, superadmin.token),
      gateway.request('get', '/dashboard/summary', undefined, superadmin.token),
      gateway.request('get', '/v1/capacity-predictions/storage_usage/101', undefined, superadmin.token),
    ]);

    expect(volumes.content[0].capacity).toMatchObject({ limit: { unit: expect.any(String) }, used: { unit: expect.any(String) } });
    expect(realtime).toMatchObject({ data_unit: 'TB', trend_meta: { quota_limit_tb: expect.any(Number) } });
    expect(monitoring).toMatchObject({ capacity_unit: 'TB' });
    expect(clusterCapacity.data_unit).toBe('TB');
    expect(clusterCapacity.capacity.start_used.unit).toEqual(expect.any(String));
    expect(clusterCapacity.data[0].capacity.used.unit).toEqual(expect.any(String));
    expect(dashboard.summary.capacity.limit_gb.unit).toEqual(expect.any(String));
    expect(forecast.data_unit).toBe('GB');
    expect(forecast.curve[0].capacity.p50.unit).toEqual(expect.any(String));
  });

  it('accepts double-slash resource paths emitted by the shared API client', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    await expect(gateway.request('get', '/storage-usages//101/realtime', undefined, superadmin.token))
      .resolves.toMatchObject({ info: { linux_path: '/data/demo/project-1/alice' } });
    await expect(gateway.request('get', '/groups//11/realtime', undefined, superadmin.token))
      .resolves.toMatchObject({ info: { name: '芯片设计项目组' } });
  });

  it('provides display fields for every mock alert table column', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);
    const alerts = await gateway.request('get', '/storage-alerts', undefined, superadmin.token);

    expect(alerts.content[0]).toMatchObject({
      alert_type: 'alert',
      cluster_name: expect.any(String),
      project_name: expect.any(String),
      related_type: 'StorageUsage',
      event_type: 'trigger',
      quota_basis: 'hard',
      delivery_status: expect.any(String),
      threshold: expect.any(Number),
      avg_use_ratio: expect.any(Number),
      related_info: { context: { group_tag: expect.any(String), linux_path: expect.any(String) } },
    });
  });

  it('provides complete audit-event details for the right-side drawer', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);
    const event = await gateway.request('get', '/v1/audit-events/1', undefined, superadmin.token);

    expect(event).toMatchObject({
      occurred_at: expect.any(String),
      outcome: expect.any(String),
      action: expect.any(String),
      actor: { rd_username: expect.any(String) },
      project: { name: expect.any(String) },
      resource_type: expect.any(String),
      resource_id: expect.any(Number),
      trace_id: expect.any(String),
      request_id: expect.any(String),
      before_summary: expect.any(Object),
      after_summary: expect.any(Object),
      metadata: expect.objectContaining({ client_ip: expect.any(String) }),
    });
  });

  it('mirrors every capacity forecast asset type on the standalone list', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const forecasts = await gateway.request('get', '/v1/forecasts', undefined, superadmin.token, {
      params: { page: 1, size: 100 },
    });

    expect(new Set(forecasts.content.map((item) => item.asset_type))).toEqual(new Set([
      'storage_cluster',
      'volume',
      'qtree',
      'group',
      'storage_usage',
    ]));
  });
});
