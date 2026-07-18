import { describe, expect, it } from 'vitest';
import { DEMO_PASSWORD, createMockGateway } from '@/mocks/runtime.js';

describe('capacity prediction mock runtime', () => {
  it('enables user-directory and project-group prediction views with panel data', async () => {
    const gateway = createMockGateway();
    const admin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const [usageAccess, groupAccess, usagePrediction, groupPlans, usageIncidents] = await Promise.all([
      gateway.request('get', '/v1/capacity-predictions/storage_usage/101/access', undefined, admin.token),
      gateway.request('get', '/v1/capacity-predictions/group/11/access', undefined, admin.token),
      gateway.request('get', '/v1/capacity-predictions/storage_usage/101', undefined, admin.token),
      gateway.request('get', '/v1/capacity-predictions/group/11/plans', undefined, admin.token),
      gateway.request('get', '/v1/capacity-predictions/storage_usage/101/related-incidents', undefined, admin.token),
    ]);

    expect(usageAccess).toMatchObject({ visible: true, can_manage_plans: true });
    expect(groupAccess).toMatchObject({ visible: true, can_manage_plans: true });
    expect(usagePrediction).toMatchObject({
      asset_type: 'storage_usage',
      asset_id: '101',
      curve: expect.any(Array),
    });
    expect(usagePrediction.curve.length).toBeGreaterThan(0);
    expect(groupPlans).toEqual(expect.arrayContaining([
      expect.objectContaining({ asset_type: 'group', asset_id: '11' }),
    ]));
    expect(usageIncidents).toEqual(expect.arrayContaining([
      expect.objectContaining({ category: 'capacity_pressure' }),
    ]));
  });
});
