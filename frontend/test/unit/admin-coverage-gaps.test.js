import { flushPromises, shallowMount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

const projectApi = { fetchById: vi.fn() };
const groupApi = { fetch: vi.fn() };
const dashboardApi = { fetchOverview: vi.fn() };

vi.mock('@/api/project-api.js', () => ({ default: projectApi }));
vi.mock('@/api/group-api.js', () => ({ default: groupApi }));
vi.mock('@/api/dashboard-api.js', () => ({ default: dashboardApi }));

describe('admin coverage gaps', () => {
  it('loads the dashboard after a project is selected', async () => {
    dashboardApi.fetchOverview.mockResolvedValue({
      scope: { mode: 'project', project_id: 7, project_name: '项目 A' },
      summary: { limit_gb: 20, used_gb: 10, available_gb: 10, use_ratio: 50, storage_cluster_count: 1, alert_count: 0 },
      capacity_trend: [],
      capacity_items: [{ id: 8, name: '项目组 A', limit_gb: 5, used_gb: 3, available_gb: 2, use_ratio: 60 }],
      alert_trend: [],
    });

    const { default: DashboardPage } = await import('@/pages/dashboard/DashboardPage.vue');
    const wrapper = shallowMount(DashboardPage);
    await wrapper.findComponent({ name: 'ProjectSelect' }).vm.$emit('update:modelValue', 7);
    await flushPromises();

    expect(dashboardApi.fetchOverview).toHaveBeenLastCalledWith({ project_id: 7 });
    expect(wrapper.findComponent({ name: 'PieCharts' }).exists()).toBe(true);
  });
});
