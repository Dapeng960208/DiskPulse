import { describe, expect, it } from 'vitest';
import {
  DEMO_PASSWORD,
  DEMO_USERS,
  createMockGateway,
} from '@/mocks/runtime.js';

describe('frontend mock runtime', () => {
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

    expect(trend.content.length).toBeGreaterThan(1);
    expect(updated.name).toBe('Mock 已更新标签');
    expect(tags.content.some((tag) => tag.id === created.id)).toBe(false);
  });
});
