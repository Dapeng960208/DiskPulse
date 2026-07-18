import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ElMessage } from 'element-plus';

const dashboardApi = {
  fetchSummary: vi.fn(),
  fetchCapacityTrend: vi.fn(),
  fetchCapacityItems: vi.fn(),
  fetchAlertLevels: vi.fn(),
  fetchTopUsers: vi.fn(),
};
const authorization = { hasRole: vi.fn() };

vi.mock('@/api/dashboard-api.js', () => ({ default: dashboardApi }));
vi.mock('@/utils/authorization', () => authorization);
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

const StorageTrendChart = defineComponent({
  name: 'StorageTrendChart',
  props: { series: Array, indicator: String, trendMeta: Object, ariaLabel: String, height: String },
  template: '<div class="storage-trend-chart-stub" />',
});

const summaryResponse = (mode = 'global') => ({
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
  trend_meta: {
    quota_basis: 'hard',
    rule_source: mode === 'project' ? 'project' : 'system',
    thresholds: { important: 80, serious: 90, emergency: 95 },
    quota_limit_gb: mode === 'project' ? 300 : 1024,
    ratio_indicator: 'used_ratio',
  },
});
const capacityTrend = [
  { timestamp: '2026-07-16T00:00:00', used_gb: 620 },
  { timestamp: '2026-07-17T00:00:00', used_gb: 640 },
];
const capacityItems = (mode = 'global') => [
  { id: 1, name: mode === 'project' ? '项目组 A' : '项目 A', limit_gb: 100, used_gb: 70, available_gb: 30, use_ratio: 70 },
];
const alertLevels = [
  { level: 'important', name: '重要', count: 3 },
  { level: 'serious', name: '严重', count: 1 },
];
const topUsers = [{ id: 9, name: 'alice', used_gb: 40 }];

async function mountPage({ flush = true } = {}) {
  const { default: DashboardPage } = await import('@/pages/dashboard/DashboardPage.vue');
  const wrapper = shallowMount(DashboardPage, {
    global: {
      stubs: {
        ProjectSelect,
        PieCharts,
        DashboardChart,
        StorageTrendChart,
        ElSkeleton: defineComponent({ name: 'ElSkeleton', template: '<div class="skeleton" />' }),
        ElEmpty: defineComponent({ name: 'ElEmpty', props: { description: String }, template: '<div class="empty">{{ description }}</div>' }),
      },
    },
  });
  if (flush) await flushPromises();
  return wrapper;
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authorization.hasRole.mockReturnValue(true);
    dashboardApi.fetchSummary.mockResolvedValue(summaryResponse());
    dashboardApi.fetchCapacityTrend.mockResolvedValue(capacityTrend);
    dashboardApi.fetchCapacityItems.mockResolvedValue(capacityItems());
    dashboardApi.fetchAlertLevels.mockResolvedValue(alertLevels);
    dashboardApi.fetchTopUsers.mockResolvedValue(topUsers);
  });

  it('loads the global overview and renders the approved chart layout', async () => {
    const wrapper = await mountPage();

    expect(dashboardApi.fetchSummary).toHaveBeenCalledWith({});
    expect(dashboardApi.fetchCapacityTrend).toHaveBeenCalledWith({});
    expect(dashboardApi.fetchCapacityItems).toHaveBeenCalledWith({});
    expect(dashboardApi.fetchAlertLevels).toHaveBeenCalledWith({});
    expect(dashboardApi.fetchTopUsers).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain('物理总容量');
    expect(wrapper.text()).toContain('项目容量对比');
    expect(wrapper.text()).toContain('1.00 TB');
    expect(wrapper.findComponent(PieCharts).props()).toMatchObject({
      variant: 'dashboard',
      centerLabel: '62.5%',
    });
    expect(wrapper.findAllComponents(DashboardChart)).toHaveLength(2);
    expect(wrapper.findComponent(StorageTrendChart).props()).toMatchObject({
      indicator: 'used',
      trendMeta: summaryResponse().trend_meta,
      ariaLabel: '近 30 天容量趋势',
    });
  });

  it('waits for a project selection instead of requesting forbidden global data for a project member', async () => {
    authorization.hasRole.mockReturnValue(false);

    const wrapper = await mountPage();

    expect(dashboardApi.fetchSummary).not.toHaveBeenCalled();
    expect(dashboardApi.fetchCapacityTrend).not.toHaveBeenCalled();
    expect(dashboardApi.fetchCapacityItems).not.toHaveBeenCalled();
    expect(dashboardApi.fetchAlertLevels).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain('请选择项目以查看存储概览');
  });

  it('reloads the same workspace as a project drill-down', async () => {
    dashboardApi.fetchSummary
      .mockResolvedValueOnce(summaryResponse())
      .mockResolvedValueOnce(summaryResponse('project'));
    dashboardApi.fetchCapacityItems
      .mockResolvedValueOnce(capacityItems())
      .mockResolvedValueOnce(capacityItems('project'));
    const wrapper = await mountPage();

    await wrapper.findComponent(ProjectSelect).vm.$emit('update:modelValue', 7);
    await flushPromises();

    expect(dashboardApi.fetchSummary).toHaveBeenLastCalledWith({ project_id: 7 });
    expect(dashboardApi.fetchCapacityTrend).toHaveBeenLastCalledWith({ project_id: 7 });
    expect(dashboardApi.fetchCapacityItems).toHaveBeenLastCalledWith({ project_id: 7 });
    expect(dashboardApi.fetchAlertLevels).toHaveBeenLastCalledWith({ project_id: 7 });
    expect(dashboardApi.fetchTopUsers).toHaveBeenCalledWith({ project_id: 7 });
    expect(wrapper.text()).toContain('项目限额');
    expect(wrapper.text()).toContain('项目组容量对比');
    expect(wrapper.text()).toContain('用户使用 Top 10');
    expect(wrapper.text()).toContain('告警级别');
    expect(wrapper.findAllComponents(DashboardChart)).toHaveLength(3);
    expect(wrapper.findComponent(StorageTrendChart).props('trendMeta').rule_source).toBe('project');
    const chartRow = wrapper.find('.dashboard-grid-secondary');
    expect(chartRow.findAll('article')).toHaveLength(3);
    expect(chartRow.attributes('style')).toContain('--dashboard-columns: 2fr 2fr 1fr');
  });

  it('keeps the dashboard structure visible while project data is loading', async () => {
    dashboardApi.fetchSummary.mockReturnValue(new Promise(() => {}));
    dashboardApi.fetchCapacityTrend.mockReturnValue(new Promise(() => {}));
    dashboardApi.fetchCapacityItems.mockReturnValue(new Promise(() => {}));
    dashboardApi.fetchAlertLevels.mockReturnValue(new Promise(() => {}));

    const wrapper = await mountPage({ flush: false });

    expect(wrapper.text()).toContain('容量趋势');
    expect(wrapper.text()).toContain('项目容量对比');
    expect(wrapper.text()).toContain('告警级别');
    expect(wrapper.findAll('.skeleton').length).toBeGreaterThan(1);
  });

  it('keeps successful panels visible when one chart request fails', async () => {
    const error = vi.spyOn(ElMessage, 'error').mockImplementation(() => undefined);
    dashboardApi.fetchCapacityTrend.mockRejectedValue(new Error('failed'));

    const wrapper = await mountPage();

    expect(error).toHaveBeenCalledWith('加载存储概览失败，请稍后重试');
    expect(wrapper.text()).toContain('物理总容量');
    expect(wrapper.text()).toContain('暂无容量趋势');
  });
});
