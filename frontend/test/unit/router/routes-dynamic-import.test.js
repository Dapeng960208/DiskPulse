import { vi } from 'vitest';
import { defineComponent, h } from 'vue';

vi.mock('echarts', () => ({
  init: vi.fn(() => ({
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    showLoading: vi.fn(),
    hideLoading: vi.fn(),
  })),
  number: Number,
  graphic: {
    LinearGradient: class LinearGradient {},
  },
}));
vi.mock('@/layouts/AppLayout.vue', () => ({ default: createRoutePageStub('AppLayout') }));

function createRoutePageStub(name) {
  return defineComponent({
    name,
    setup() {
      return () => h('div', name);
    },
  });
}

vi.mock('@/pages/auth/LoginPage.vue', () => ({ default: createRoutePageStub('LoginPage') }));
vi.mock('@/pages/dashboard/DashboardPage.vue', () => ({ default: createRoutePageStub('DashboardPage') }));
vi.mock('@/pages/usage/UsageListPage.vue', () => ({ default: createRoutePageStub('UsageListPage') }));
vi.mock('@/pages/usage/UsageDetailPage.vue', () => ({ default: createRoutePageStub('UsageDetailPage') }));
vi.mock('@/pages/capacity-prediction/CapacityPredictionDetailPage.vue', () => ({ default: createRoutePageStub('CapacityPredictionDetailPage') }));
vi.mock('@/pages/capacity-prediction/CapacityPredictionListPage.vue', () => ({ default: createRoutePageStub('CapacityPredictionListPage') }));
vi.mock('@/pages/project/ProjectListPage.vue', () => ({ default: createRoutePageStub('ProjectListPage') }));
vi.mock('@/pages/project/ProjectDetailPage.vue', () => ({ default: createRoutePageStub('ProjectDetailPage') }));
vi.mock('@/pages/group/GroupListPage.vue', () => ({ default: createRoutePageStub('GroupListPage') }));
vi.mock('@/pages/group/GroupDetailPage.vue', () => ({ default: createRoutePageStub('GroupDetailPage') }));
vi.mock('@/pages/ai/AiChatPage.vue', () => ({ default: createRoutePageStub('AiChatPage') }));
// Review source: IncidentCenter became a lazy route after this exhaustive loader contract was written.
// Resolution: mock the new page and include its loader in the guarded route total.
vi.mock('@/pages/incident/IncidentCenterPage.vue', () => ({ default: createRoutePageStub('IncidentCenterPage') }));
vi.mock('@/pages/alert/AlertListPage.vue', () => ({ default: createRoutePageStub('AlertListPage') }));
vi.mock('@/pages/admin/storage-cluster/StorageClusterListPage.vue', () => ({ default: createRoutePageStub('StorageClusterListPage') }));
vi.mock('@/pages/admin/storage-cluster/StorageClusterDetailPage.vue', () => ({ default: createRoutePageStub('StorageClusterDetailPage') }));
vi.mock('@/pages/group-tag/GroupTagListPage.vue', () => ({ default: createRoutePageStub('GroupTagListPage') }));
vi.mock('@/pages/admin/aggregate/AggregateListPage.vue', () => ({ default: createRoutePageStub('AggregateListPage') }));
vi.mock('@/pages/admin/aggregate/AggregateDetailPage.vue', () => ({ default: createRoutePageStub('AggregateDetailPage') }));
vi.mock('@/pages/admin/volume/VolumeListPage.vue', () => ({ default: createRoutePageStub('VolumeListPage') }));
vi.mock('@/pages/admin/volume/VolumeDetailPage.vue', () => ({ default: createRoutePageStub('VolumeDetailPage') }));
vi.mock('@/pages/admin/qtree/QtreeListPage.vue', () => ({ default: createRoutePageStub('QtreeListPage') }));
vi.mock('@/pages/admin/qtree/QtreeDetailPage.vue', () => ({ default: createRoutePageStub('QtreeDetailPage') }));
vi.mock('@/pages/admin/user/UserListPage.vue', () => ({ default: createRoutePageStub('UserListPage') }));
vi.mock('@/pages/admin/backup/BackUpListPage.vue', () => ({ default: createRoutePageStub('BackUpListPage') }));
vi.mock('@/pages/admin/settings/SettingsPage.vue', () => ({ default: createRoutePageStub('SettingsPage') }));
vi.mock('@/pages/admin/ai/AiCenterPage.vue', () => ({ default: createRoutePageStub('AiCenterPage') }));
vi.mock('@/pages/admin/forecast-governance/ForecastGovernancePage.vue', () => ({ default: createRoutePageStub('ForecastGovernancePage') }));
vi.mock('@/pages/admin/ai/AiAuditDetailPage.vue', () => ({ default: createRoutePageStub('AiAuditDetailPage') }));
vi.mock('@/pages/admin/audit/AuditEventListPage.vue', () => ({ default: createRoutePageStub('AuditEventListPage') }));
vi.mock('@/pages/admin/audit/AuditEventDetailPage.vue', () => ({ default: createRoutePageStub('AuditEventDetailPage') }));
vi.mock('@/pages/error/UnauthorizedPage.vue', () => ({ default: createRoutePageStub('UnauthorizedPage') }));
vi.mock('@/pages/error/NotFoundPage.vue', () => ({ default: createRoutePageStub('NotFoundPage') }));

const { default: routes } = await import('@/router/routes');

function collectLazyComponents(routeList, bucket = []) {
  routeList.forEach((route) => {
    if (typeof route.component === 'function') {
      bucket.push(route.component);
    }

    if (route.children) {
      collectLazyComponents(route.children, bucket);
    }
  });

  return bucket;
}

describe('router lazy route components', () => {
  it('invokes every lazy route component loader', async () => {
    const lazyComponents = collectLazyComponents(routes);

    expect(lazyComponents).toHaveLength(33);

    await Promise.all(lazyComponents.map((loadComponent) => loadComponent().catch(() => null)));
  });
});
