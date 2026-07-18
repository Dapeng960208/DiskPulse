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
});
