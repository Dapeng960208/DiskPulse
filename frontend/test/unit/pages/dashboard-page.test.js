import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ElMessage } from 'element-plus';

const dashboardApi = { fetchOverview: vi.fn() };

vi.mock('@/api/dashboard-api.js', () => ({ default: dashboardApi }));
vi.mock('@/api/project-api.js', () => ({ default: { fetchById: vi.fn(), fetch: vi.fn() } }));
vi.mock('@/api/group-api.js', () => ({ default: { fetch: vi.fn() } }));
vi.mock('@/components/form/ProjectSelect.vue', () => ({
  default: { name: 'ProjectSelect', template: '<button />' },
}));
vi.mock('@/common/charts/PieCharts.vue', () => ({
  default: { name: 'PieCharts', template: '<div />' },
}));
vi.mock('@/common/charts/BarStackChart.vue', () => ({
  default: { name: 'BarStackChart', template: '<div />' },
}));

const ProjectSelect = defineComponent({
  name: 'ProjectSelect',
  props: { modelValue: [Number, String], placeholder: String },
  emits: ['update:modelValue'],
  setup(_, { emit }) {
    return () => h('button', { class: 'project-select', onClick: () => emit('update:modelValue', 7) }, 'project');
  },
});

const PieCharts = defineComponent({
  name: 'PieCharts',
  props: { data: Array, title: String, variant: String, centerLabel: String },
  template: '<div class="pie-chart-stub" />',
});

const DashboardChart = defineComponent({
  name: 'DashboardChart',
  props: { option: Object, ariaLabel: String, height: String },
  template: '<div class="dashboard-chart-stub" />',
});

const response = (mode = 'global') => ({
  scope: {
    mode,
    project_id: mode === 'project' ? 7 : null,
    project_name: mode === 'project' ? '项目 A' : null,
    updated_at: '2026-07-17T09:42:00',
  },
  summary: {
    limit_gb: mode === 'project' ? 300 : 1024,
    used_gb: mode === 'project' ? 200 : 640,
    available_gb: mode === 'project' ? 100 : 384,
    use_ratio: mode === 'project' ? 66.67 : 62.5,
    storage_cluster_count: mode === 'project' ? 1 : 6,
    alert_count: 3,
  },
  capacity_trend: [
    { timestamp: '2026-07-16T00:00:00', used_gb: 620 },
    { timestamp: '2026-07-17T00:00:00', used_gb: 640 },
  ],
  capacity_items: [
    { id: 1, name: mode === 'project' ? '项目组 A' : '项目 A', limit_gb: 100, used_gb: 70, available_gb: 30, use_ratio: 70 },
  ],
  alert_trend: [{ date: '2026-07-17', count: 3 }],
});

async function mountPage() {
  const { default: DashboardPage } = await import('@/pages/dashboard/DashboardPage.vue');
  const wrapper = shallowMount(DashboardPage, {
    global: {
      stubs: {
        ProjectSelect,
        PieCharts,
        DashboardChart,
        ElSkeleton: defineComponent({ name: 'ElSkeleton', template: '<div class="skeleton" />' }),
        ElEmpty: defineComponent({ name: 'ElEmpty', props: { description: String }, template: '<div class="empty">{{ description }}</div>' }),
      },
    },
  });
  await flushPromises();
  return wrapper;
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    dashboardApi.fetchOverview.mockResolvedValue(response());
  });

  it('loads the global overview and renders the approved chart layout', async () => {
    const wrapper = await mountPage();

    expect(dashboardApi.fetchOverview).toHaveBeenCalledWith({});
    expect(wrapper.text()).toContain('物理总容量');
    expect(wrapper.text()).toContain('项目容量对比');
    expect(wrapper.text()).toContain('1.00 TB');
    expect(wrapper.findComponent(PieCharts).props()).toMatchObject({
      variant: 'dashboard',
      centerLabel: '62.5%',
    });
    expect(wrapper.findAllComponents(DashboardChart)).toHaveLength(3);
  });

  it('reloads the same workspace as a project drill-down', async () => {
    dashboardApi.fetchOverview
      .mockResolvedValueOnce(response())
      .mockResolvedValueOnce(response('project'));
    const wrapper = await mountPage();

    await wrapper.findComponent(ProjectSelect).vm.$emit('update:modelValue', 7);
    await flushPromises();

    expect(dashboardApi.fetchOverview).toHaveBeenLastCalledWith({ project_id: 7 });
    expect(wrapper.text()).toContain('项目限额');
    expect(wrapper.text()).toContain('项目组容量对比');
  });

  it('shows a stable empty state when loading fails', async () => {
    const error = vi.spyOn(ElMessage, 'error').mockImplementation(() => undefined);
    dashboardApi.fetchOverview.mockRejectedValue(new Error('failed'));

    const wrapper = await mountPage();

    expect(error).toHaveBeenCalledWith('加载存储概览失败，请稍后重试');
    expect(wrapper.text()).toContain('暂无概览数据');
  });
});
