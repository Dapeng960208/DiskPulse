import { flushPromises, shallowMount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

const projectApi = { fetchById: vi.fn() };
const groupApi = { fetch: vi.fn() };
const dashboardApi = {
  fetchSummary: vi.fn(),
  fetchCapacityTrend: vi.fn(),
  fetchCapacityItems: vi.fn(),
  fetchAlertLevels: vi.fn(),
  fetchTopUsers: vi.fn(),
};
const authorization = { hasRole: vi.fn() };

vi.mock('@/api/project-api.js', () => ({ default: projectApi }));
vi.mock('@/api/group-api.js', () => ({ default: groupApi }));
vi.mock('@/api/dashboard-api.js', () => ({ default: dashboardApi }));
vi.mock('@/utils/authorization', () => authorization);

describe('admin coverage gaps', () => {
  it('loads the dashboard after a project is selected', async () => {
    // Review fix verification: legacy shallow mounts must provide the dashboard role boundary.
    authorization.hasRole.mockReturnValue(true);
    dashboardApi.fetchSummary.mockResolvedValue({
      scope: { mode: 'project', project_id: 7, project_name: '项目 A' },
      summary: { limit_gb: 20, used_gb: 10, available_gb: 10, use_ratio: 50, storage_cluster_count: 1, alert_count: 0 },
    });
    dashboardApi.fetchCapacityTrend.mockResolvedValue([]);
    dashboardApi.fetchCapacityItems.mockResolvedValue([
      { id: 8, name: '项目组 A', limit_gb: 5, used_gb: 3, available_gb: 2, use_ratio: 60 },
    ]);
    dashboardApi.fetchAlertLevels.mockResolvedValue([]);
    dashboardApi.fetchTopUsers.mockResolvedValue([]);

    const { default: DashboardPage } = await import('@/pages/dashboard/DashboardPage.vue');
    const wrapper = shallowMount(DashboardPage);
    await wrapper.findComponent({ name: 'ProjectSelect' }).vm.$emit('update:modelValue', 7);
    await flushPromises();

    expect(dashboardApi.fetchSummary).toHaveBeenLastCalledWith({ project_id: 7 });
    expect(wrapper.findComponent({ name: 'PieCharts' }).exists()).toBe(true);
  });
});
