import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/support/base-request', () => ({
  default: {},
}));

vi.mock('@/api/support/auth-request', () => ({
  default: {},
}));

import groupApi from '@/api/group-api';
import projectApi from '@/api/project-api';
import environmentApi from '@/api/project-storage-environment-api';
import DashboardPage from '@/pages/dashboard/DashboardPage.vue';

const ProjectSelectStub = defineComponent({
  name: 'ProjectSelect',
  props: { modelValue: Number },
  emits: ['update:modelValue'],
  setup(_, { slots }) {
    return () => h('div', { 'data-test': 'project-select' }, slots.default?.());
  },
});

const ProjectStorageEnvironmentSelectStub = defineComponent({
  name: 'ProjectStorageEnvironmentSelect',
  props: {
    modelValue: Number,
    projectId: Number,
    clearable: Boolean,
  },
  emits: ['update:modelValue'],
  setup(_, { slots }) {
    return () => h('div', { 'data-test': 'environment-select' }, slots.default?.());
  },
});

const BarStackChartStub = defineComponent({
  name: 'BarStackChart',
  props: {
    title: String,
    categories: Array,
    data: Array,
    seriesNames: Array,
  },
  setup(props) {
    return () => h('div', { 'data-test': 'group-series' }, props.title);
  },
});

const mountedWrappers = [];

afterEach(() => {
  mountedWrappers.splice(0).forEach((wrapper) => wrapper.unmount());
  vi.restoreAllMocks();
});

async function mountDashboard({
  environments = [],
  groups = [],
  project = { id: 1, name: 'Project A', limit: 200, used: 100 },
} = {}) {
  vi.spyOn(projectApi, 'fetchById').mockResolvedValue(project);
  vi.spyOn(projectApi, 'fetchStorageSummary').mockResolvedValue({ data: [], tree: [] });
  vi.spyOn(projectApi, 'fetchGroupStorage').mockResolvedValue({ data: {} });
  vi.spyOn(environmentApi, 'fetchByProject').mockResolvedValue({
    content: environments,
    total: environments.length,
  });
  vi.spyOn(groupApi, 'fetch').mockResolvedValue({
    content: groups,
    total: groups.length,
  });

  const wrapper = shallowMount(DashboardPage, {
    global: {
      stubs: {
        BarStackChart: BarStackChartStub,
        ProjectSelect: ProjectSelectStub,
        ProjectStorageEnvironmentSelect: ProjectStorageEnvironmentSelectStub,
      },
    },
  });
  mountedWrappers.push(wrapper);
  await flushPromises();
  return wrapper;
}

async function selectProject(wrapper, projectId = 1) {
  const projectSelect = wrapper.findComponent(ProjectSelectStub);
  expect(projectSelect.exists()).toBe(true);
  projectSelect.vm.$emit('update:modelValue', projectId);
  await flushPromises();
  return projectSelect;
}

describe('project environment dashboard', () => {
  it('cascades project and environment filters through existing APIs', async () => {
    const environments = [
      { id: 11, name: 'Environment A', project_id: 1, is_active: true },
      { id: 12, name: 'Environment B', project_id: 1, is_active: true },
    ];
    const wrapper = await mountDashboard({ environments });

    await selectProject(wrapper);

    expect(projectApi.fetchById).toHaveBeenCalledWith(1);
    expect(environmentApi.fetchByProject).toHaveBeenCalledWith(1, {
      page: 1,
      size: 100,
    });
    expect(groupApi.fetch).toHaveBeenCalledWith({
      project_id: 1,
      page: 1,
      size: 100,
    });

    const environmentSelect = wrapper.findComponent(ProjectStorageEnvironmentSelectStub);
    expect(environmentSelect.props()).toEqual(expect.objectContaining({
      projectId: 1,
      clearable: true,
    }));
    environmentSelect.vm.$emit('update:modelValue', 11);
    await flushPromises();

    expect(groupApi.fetch).toHaveBeenLastCalledWith({
      project_environment_id: 11,
      page: 1,
      size: 100,
    });
  });

  it('keeps same-name groups separate with environment-scoped keys and labels', async () => {
    const environments = [
      { id: 11, name: 'Environment A', project_id: 1, is_active: true },
      { id: 12, name: 'Environment B', project_id: 1, is_active: true },
    ];
    const groups = [
      {
        id: 101,
        name: 'Shared Group',
        project_environment_id: 11,
        project_environment: { id: 11, name: 'Environment A' },
        used: 30,
        limit: 100,
      },
      {
        id: 202,
        name: 'Shared Group',
        project_environment_id: 12,
        project_environment: { id: 12, name: 'Environment B' },
        used: 70,
        limit: 100,
      },
    ];
    const wrapper = await mountDashboard({ environments, groups });

    await selectProject(wrapper);

    const series = wrapper.findAllComponents(BarStackChartStub);
    expect(series).toHaveLength(2);
    expect(series.map((chart) => chart.props('title'))).toEqual([
      'Environment A · Shared Group',
      'Environment B · Shared Group',
    ]);
    expect(series.map((chart) => chart.vm.$.vnode.key)).toEqual([
      '11:101',
      '12:202',
    ]);
  });

  it('shows the project aggregate separately from each environment capacity', async () => {
    const environments = [
      { id: 11, name: 'Environment A', project_id: 1, is_active: true, limit: 100, used: 30 },
      { id: 12, name: 'Environment B', project_id: 1, is_active: true, limit: 100, used: 70 },
    ];
    const wrapper = await mountDashboard({ environments });

    await selectProject(wrapper);

    const projectOverview = wrapper.find('[data-test="project-capacity-overview"]');
    expect(projectOverview.text()).toContain('Project A');
    expect(projectOverview.text()).toContain('100');
    expect(projectOverview.text()).toContain('200');

    const environmentA = wrapper.find('[data-test="environment-capacity-11"]');
    const environmentB = wrapper.find('[data-test="environment-capacity-12"]');
    expect(environmentA.text()).toContain('Environment A');
    expect(environmentA.text()).toContain('30');
    expect(environmentA.text()).toContain('100');
    expect(environmentB.text()).toContain('Environment B');
    expect(environmentB.text()).toContain('70');
    expect(environmentB.text()).toContain('100');
  });
});
