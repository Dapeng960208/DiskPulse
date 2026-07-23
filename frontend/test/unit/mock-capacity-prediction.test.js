import { describe, expect, it } from 'vitest';
import { DEMO_PASSWORD, createMockGateway } from '@/mocks/runtime.js';

describe('capacity prediction mock runtime', () => {
  it('serves lightweight exhaustion risk for all four dimensions', async () => {
    const gateway = createMockGateway();
    const admin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const risks = await Promise.all([
      gateway.request('get', '/v1/capacity-predictions/storage_cluster/1/risk', undefined, admin.token),
      gateway.request('get', '/v1/capacity-predictions/project/1/risk', undefined, admin.token),
      gateway.request('get', '/v1/capacity-predictions/group/11/risk', undefined, admin.token),
      gateway.request('get', '/v1/capacity-predictions/storage_usage/101/risk', undefined, admin.token),
    ]);

    expect(risks).toHaveLength(4);
    risks.forEach((risk) => expect(risk).toMatchObject({
      level: expect.stringMatching(/^(critical|high|watch|none|insufficient)$/),
      label: expect.any(String),
      reason: expect.any(String),
      horizon_days: 30,
    }));
  });

  it('keeps Incident AI settings behind the super-admin boundary and preserves candidate order', async () => {
    const gateway = createMockGateway();
    const admin = await gateway.login('demo-superadmin', DEMO_PASSWORD);
    const reader = await gateway.login('demo-reader', DEMO_PASSWORD);

    await expect(gateway.request('get', '/v1/admin/incident-ai-settings', undefined, reader.token))
      .rejects.toMatchObject({ status: 403 });
    const saved = await gateway.request('patch', '/v1/admin/incident-ai-settings', {
      enabled: true,
      model_ids: [2, 1],
      iops_absolute_floor: 12,
      iops_baseline_ratio: 0.08,
    }, admin.token);

    expect(saved.model_ids).toEqual([2, 1]);
    expect(saved.models.map((model) => model.id)).toEqual([2, 1]);
    expect(saved).toMatchObject({ enabled: true, iops_absolute_floor: 12, iops_baseline_ratio: 0.08 });
  });
});
