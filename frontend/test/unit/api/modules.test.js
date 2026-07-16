import { vi } from 'vitest';

vi.mock('@/api/support/base-request', () => ({
  default: {},
}));

vi.mock('@/api/support/auth-request', () => ({
  default: {},
}));

const { default: BaseApi } = await import('@/api/support/base-api');

describe('api modules', () => {
  const getSpy = vi.spyOn(BaseApi.prototype, 'get').mockResolvedValue({ ok: true });
  const postSpy = vi.spyOn(BaseApi.prototype, 'post').mockResolvedValue({ ok: true });
  const putSpy = vi.spyOn(BaseApi.prototype, 'put').mockResolvedValue({ ok: true });
  const patchSpy = vi.spyOn(BaseApi.prototype, 'patch').mockResolvedValue({ ok: true });
  const deleteSpy = vi.spyOn(BaseApi.prototype, 'delete').mockResolvedValue({ ok: true });
  const exportSpy = vi.spyOn(BaseApi.prototype, 'export').mockResolvedValue({ ok: true });

  afterAll(() => {
    getSpy.mockRestore();
    postSpy.mockRestore();
    putSpy.mockRestore();
    patchSpy.mockRestore();
    deleteSpy.mockRestore();
    exportSpy.mockRestore();
  });

  it('maps wrapper methods to REST endpoints', async () => {
    const { default: accountApi } = await import('@/api/account-api');
    const { default: aggregateApi } = await import('@/api/aggregate-api');
    const { default: alertApi } = await import('@/api/alert-api');
    const { default: configApi } = await import('@/api/config-api');
    const { default: departmentApi } = await import('@/api/department-api');
    const { default: domainGroupApi } = await import('@/api/domain-group-api');
    const { default: groupApi } = await import('@/api/group-api');
    const { default: hostApi } = await import('@/api/host-api');
    const { default: projectApi } = await import('@/api/project-api');
    const { default: qtreeApi } = await import('@/api/qtree-api');
    const { default: sessionApi } = await import('@/api/session-api');
    const { default: storageBackUpRecordApi } = await import('@/api/storage-back-up-record-api');
    const { default: storageClusterApi } = await import('@/api/storage-cluster-api');
    const { default: storageUsageApi } = await import('@/api/storage-usage-api');
    const { default: usersApi } = await import('@/api/users-api');
    const { default: volumeApi } = await import('@/api/volume-api');

    await accountApi.fetchProfile();
    await accountApi.fetchProfile(3);
    await aggregateApi.fetchAggregateTrees({ page: 1 });
    await aggregateApi.fetchAggregateTreeById(1, { detail: true });
    await aggregateApi.fetchStorageRealTimeDataById(2, { range: 'day' });
    await alertApi.fetch({ page: 1 });
    await configApi.updateConfig({ enabled: true });
    await departmentApi.fetchTopLevel();
    await domainGroupApi.fetch({ page: 1 });
    await groupApi.fetchStorageRealTimeDataById(5, { detail: true });
    await groupApi.adjustQuota(5, { hard_limit: 100, unit: 'GiB' });
    await hostApi.fetchResource(1, { metric: 'cpu' });
    await hostApi.fetchSummary(1);
    await projectApi.fetchStorageRealTimeDataById(6, {});
    await projectApi.fetchStorageSummary({});
    await projectApi.fetchStorageTreeById(7, {});
    await projectApi.fetchGroupStorage({});
    await qtreeApi.fetchStorageRealTimeDataById(8, {});
    await sessionApi.login('user', 'password');
    await sessionApi.logout();
    await storageBackUpRecordApi.rollBackedBackUpStorageById(9);
    await storageClusterApi.fetchStorageRealTimeDataById(10, {});
    await storageUsageApi.fetchStorageRealTimeDataById(11, {});
    await storageUsageApi.exportStorageUsages({});
    await storageUsageApi.backUpStorageUsageById(12);
    await storageUsageApi.adjustQuota(12, { hard_limit: 50, unit: 'GiB' });
    await usersApi.login('user', 'password');
    await usersApi.logout();
    await usersApi.fetchProfile();
    await usersApi.fetchSummaryById(13, { view: 'summary' });
    await volumeApi.fetchStorageRealTimeDataById(14, {});

    expect(getSpy).toHaveBeenCalledWith('/current/profile', null, { errorHandlerDisabled: true });
    expect(getSpy).toHaveBeenCalledWith('/3/profile');
    expect(getSpy).toHaveBeenCalledWith('/storage-trees/', { page: 1 });
    expect(getSpy).toHaveBeenCalledWith('/1/storage-tree', { detail: true });
    expect(getSpy).toHaveBeenCalledWith('/2/realtime', { range: 'day' });
    expect(putSpy).toHaveBeenCalledWith('', { enabled: true });
    expect(getSpy).toHaveBeenCalledWith('/top-level');
    expect(postSpy).toHaveBeenCalledWith('', { username: 'user', password: 'password' });
    expect(deleteSpy).toHaveBeenCalledWith('');
    expect(exportSpy).toHaveBeenCalledWith('/export/', {});
    expect(patchSpy).toHaveBeenCalledWith('/5/quota', { hard_limit: 100, unit: 'GiB' });
    expect(patchSpy).toHaveBeenCalledWith('/12/quota', { hard_limit: 50, unit: 'GiB' });
  });
});
