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
    const { default: capacityPredictionApi } = await import('@/api/capacity-prediction-api');
    const { default: dashboardApi } = await import('@/api/dashboard-api');
    const { default: departmentApi } = await import('@/api/department-api');
    const { default: domainGroupApi } = await import('@/api/domain-group-api');
    const { default: groupApi } = await import('@/api/group-api');
    const { default: hostApi } = await import('@/api/host-api');
    const { default: incidentApi } = await import('@/api/incident-api');
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
    await capacityPredictionApi.visibility();
    await capacityPredictionApi.fetchPredictions({ page: 1, size: 20 });
    await capacityPredictionApi.access('group', 7);
    await capacityPredictionApi.fetchPrediction('storage_usage', 8);
    await capacityPredictionApi.fetchRisk('project', 6);
    await capacityPredictionApi.fetchPlans('group', 7);
    await capacityPredictionApi.fetchRelatedIncidents('storage_usage', 8);
    await capacityPredictionApi.createPlan('group', 7, { capacity_delta: 10 });
    await capacityPredictionApi.settings();
    await capacityPredictionApi.updateSettings({ user_visible: true });
    await capacityPredictionApi.fetchCandidates();
    await capacityPredictionApi.createCandidate({ version: 'capacity-ai-v2', ai_model_id: 3 });
    await capacityPredictionApi.activateCandidate(9);
    await dashboardApi.fetchSummary({ project_id: 7 });
    await dashboardApi.fetchCapacityTrend({ project_id: 7 });
    await dashboardApi.fetchCapacityItems({ project_id: 7 });
    await dashboardApi.fetchAlertLevels({ project_id: 7 });
    await dashboardApi.fetchTopUsers({ project_id: 7 });
    await departmentApi.fetchTopLevel();
    await domainGroupApi.fetch({ page: 1 });
    await groupApi.fetchStorageRealTimeDataById(5, { detail: true });
    await groupApi.adjustQuota(5, { hard_limit: 100, unit: 'GiB' });
    await groupApi.reconcileQuota(5);
    await groupApi.quotaHistory(5);
    await hostApi.fetchResource(1, { metric: 'cpu' });
    await hostApi.fetchSummary(1);
    await incidentApi.fetchIncident(21);
    await incidentApi.fetchDiagnosis(21);
    await incidentApi.updateIncident(21, { status: 'resolved' });
    await incidentApi.createComment(21, { content: 'checked' });
    await incidentApi.createMaintenanceWindow({ starts_at: '2026-07-21T00:00:00Z' });
    await projectApi.fetchStorageRealTimeDataById(6, {});
    await projectApi.fetchStorageSummary({});
    await projectApi.fetchStorageTreeById(7, {});
    await projectApi.fetchGroupStorage({});
    await qtreeApi.fetchStorageRealTimeDataById(8, {});
    await sessionApi.login('user', 'password');
    await sessionApi.logout();
    await storageBackUpRecordApi.rollBackedBackUpStorageById(9);
    await storageClusterApi.fetchStorageRealTimeDataById(10, {});
    await storageClusterApi.fetchSystemEvents(10, { page: 1 });
    await storageUsageApi.fetchStorageRealTimeDataById(11, {});
    await storageUsageApi.exportStorageUsages({});
    await storageUsageApi.backUpStorageUsageById(12);
    await storageUsageApi.adjustQuota(12, { hard_limit: 50, unit: 'GiB' });
    await storageUsageApi.reconcileQuota(12);
    await storageUsageApi.quotaHistory(12);
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
    expect(getSpy).toHaveBeenCalledWith('/capacity-predictions/visibility');
    expect(getSpy).toHaveBeenCalledWith('/capacity-predictions', { page: 1, size: 20 });
    expect(getSpy).toHaveBeenCalledWith('/capacity-predictions/group/7/access');
    expect(getSpy).toHaveBeenCalledWith('/capacity-predictions/storage_usage/8');
    expect(getSpy).toHaveBeenCalledWith('/capacity-predictions/project/6/risk');
    expect(getSpy).toHaveBeenCalledWith('/capacity-predictions/group/7/plans');
    expect(getSpy).toHaveBeenCalledWith('/capacity-predictions/storage_usage/8/related-incidents');
    expect(getSpy).toHaveBeenCalledWith('/12/quota/history');
    expect(getSpy).toHaveBeenCalledWith('/incidents/21');
    expect(getSpy).toHaveBeenCalledWith('/incidents/21/diagnosis');
    expect(getSpy).toHaveBeenCalledWith('/10/analytics/system-events', { page: 1 });
    expect(postSpy).toHaveBeenCalledWith('/capacity-predictions/group/7/plans', { capacity_delta: 10 });
    expect(getSpy).toHaveBeenCalledWith('/admin/capacity-prediction-settings');
    expect(patchSpy).toHaveBeenCalledWith('/admin/capacity-prediction-settings', { user_visible: true });
    expect(getSpy).toHaveBeenCalledWith('/admin/capacity-prediction-candidates');
    expect(postSpy).toHaveBeenCalledWith('/admin/capacity-prediction-candidates', { version: 'capacity-ai-v2', ai_model_id: 3 });
    expect(postSpy).toHaveBeenCalledWith('/admin/capacity-prediction-candidates/9/activate');
    expect(postSpy).toHaveBeenCalledWith('/5/quota/reconcile');
    expect(postSpy).toHaveBeenCalledWith('/12/quota/reconcile');
    expect(postSpy).toHaveBeenCalledWith('/incidents/21/comments', { content: 'checked' });
    expect(postSpy).toHaveBeenCalledWith('/maintenance-windows', { starts_at: '2026-07-21T00:00:00Z' });
    expect(getSpy).toHaveBeenCalledWith('/summary', { project_id: 7 });
    expect(getSpy).toHaveBeenCalledWith('/capacity-trend', { project_id: 7 });
    expect(getSpy).toHaveBeenCalledWith('/capacity-items', { project_id: 7 });
    expect(getSpy).toHaveBeenCalledWith('/alert-levels', { project_id: 7 });
    expect(getSpy).toHaveBeenCalledWith('/top-users', { project_id: 7 });
    expect(getSpy).toHaveBeenCalledWith('/top-level');
    expect(postSpy).toHaveBeenCalledWith('', { username: 'user', password: 'password' });
    expect(deleteSpy).toHaveBeenCalledWith('');
    expect(exportSpy).toHaveBeenCalledWith('/export/', {});
    expect(patchSpy).toHaveBeenCalledWith('/5/quota', { hard_limit: 100, unit: 'GiB' });
    expect(patchSpy).toHaveBeenCalledWith('/12/quota', { hard_limit: 50, unit: 'GiB' });
    expect(patchSpy).toHaveBeenCalledWith('/incidents/21', { status: 'resolved' });
  });
});
