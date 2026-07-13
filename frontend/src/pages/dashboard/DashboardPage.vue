<script setup>
import { computed, ref, watch } from 'vue';
import groupApi from '@/api/group-api.js';
import projectApi from '@/api/project-api.js';
import environmentApi from '@/api/project-storage-environment-api.js';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import ProjectStorageEnvironmentSelect from '@/components/form/ProjectStorageEnvironmentSelect.vue';
import BarStackChart from '@/common/charts/BarStackChart.vue';
import PieCharts from '@/common/charts/PieCharts.vue';

const projectId = ref(null);
const environmentId = ref(null);
const project = ref(null);
const environments = ref([]);
const groups = ref([]);

const visibleEnvironments = computed(() => (
  environmentId.value
    ? environments.value.filter((environment) => environment.id === environmentId.value)
    : environments.value
));

watch(projectId, loadProjectContext);
watch([projectId, environmentId], loadGroups);

function selectProject(value) {
  environmentId.value = null;
  projectId.value = value;
}

function selectEnvironment(value) {
  environmentId.value = value;
}

async function loadProjectContext(selectedProjectId) {
  project.value = null;
  environments.value = [];
  if (!selectedProjectId) return;

  try {
    const [projectResult, environmentResult] = await Promise.all([
      projectApi.fetchById(selectedProjectId),
      environmentApi.fetchByProject(selectedProjectId, { page: 1, size: 100 }),
    ]);
    project.value = projectResult;
    environments.value = environmentResult.content;
  } catch {
    project.value = null;
    environments.value = [];
  }
}

async function loadGroups([selectedProjectId, selectedEnvironmentId]) {
  groups.value = [];
  if (!selectedProjectId) return;

  const scope = selectedEnvironmentId
    ? { project_environment_id: selectedEnvironmentId }
    : { project_id: selectedProjectId };
  try {
    const result = await groupApi.fetch({ ...scope, page: 1, size: 100 });
    groups.value = result.content;
  } catch {
    groups.value = [];
  }
}

function capacityData(item) {
  const used = Number(item?.used) || 0;
  const limit = Number(item?.limit) || 0;
  return [
    ['已使用', used],
    ['可使用', Math.max(limit - used, 0)],
  ];
}

function groupChartData(group) {
  const used = Number(group.used) || 0;
  const limit = Number(group.limit) || 0;
  return [[used], [Math.max(limit - used, 0)]];
}

function groupEnvironmentName(group) {
  return group.project_environment?.name
    || environments.value.find((environment) => environment.id === group.project_environment_id)?.name
    || '未命名环境';
}
</script>

<template>
  <div class="dashboard-page">
    <div class="dashboard-card dashboard-filter">
      <ProjectSelect
        :model-value="projectId"
        clearable
        @update:model-value="selectProject" />
      <ProjectStorageEnvironmentSelect
        :model-value="environmentId"
        :project-id="projectId"
        clearable
        @update:model-value="selectEnvironment" />
    </div>

    <div
      v-if="project"
      class="dashboard-card capacity-card">
      <div data-test="project-capacity-overview">
        <strong>{{ project.name }} · 项目总览</strong>
        <span>{{ project.used ?? 0 }} / {{ project.limit ?? 0 }} GB</span>
      </div>
      <PieCharts
        :data="capacityData(project)"
        :title="`${project.name} · 项目总览`"
        width="100%"
        height="280px" />
    </div>

    <div
      v-if="visibleEnvironments.length"
      class="dashboard-grid">
      <div
        v-for="environment in visibleEnvironments"
        :key="environment.id"
        class="dashboard-card capacity-card">
        <div :data-test="`environment-capacity-${environment.id}`">
          <strong>{{ environment.name }}</strong>
          <span>{{ environment.used ?? 0 }} / {{ environment.limit ?? 0 }} GB</span>
        </div>
        <PieCharts
          :data="capacityData(environment)"
          :title="environment.name"
          width="100%"
          height="280px" />
      </div>
    </div>

    <div
      v-if="groups.length"
      class="dashboard-grid">
      <BarStackChart
        v-for="group in groups"
        :key="`${group.project_environment_id}:${group.id}`"
        class="dashboard-card group-chart"
        :series-names="['used', 'available']"
        :data="groupChartData(group)"
        :categories="[group.name]"
        :series-map="{ used: '已使用(GB)', available: '可使用(GB)' }"
        :title="`${groupEnvironmentName(group)} · ${group.name}`"
        width="100%"
        height="100%" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
@import '@/styles/mixins.scss';

.dashboard-page {
  display: grid;
  gap: var(--spacing-xl);
}

.dashboard-card {
  @include card-base;
  border: 1px solid var(--border-color);
  padding: var(--spacing-lg);
}

.dashboard-filter,
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-lg);
}

.dashboard-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.group-chart {
  height: 700px;
}

.capacity-card strong,
.capacity-card span {
  display: block;
}

.capacity-card span {
  margin-top: var(--spacing-xs);
  color: var(--text-secondary);
}

@include mobile {
  .dashboard-filter,
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
