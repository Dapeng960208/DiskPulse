<script setup>
import { ref, watch } from 'vue';
import groupApi from '@/api/group-api.js';
import projectApi from '@/api/project-api.js';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import BarStackChart from '@/common/charts/BarStackChart.vue';
import PieCharts from '@/common/charts/PieCharts.vue';

const projectId = ref(null);
const project = ref(null);
const groups = ref([]);

watch(projectId, async (selectedProjectId) => {
  project.value = null;
  groups.value = [];
  if (!selectedProjectId) return;
  try {
    const [projectResult, groupResult] = await Promise.all([
      projectApi.fetchById(selectedProjectId),
      groupApi.fetch({ project_id: selectedProjectId, page: 1, size: 100 }),
    ]);
    project.value = projectResult;
    groups.value = groupResult.content;
  } catch {
    project.value = null;
    groups.value = [];
  }
});

function capacityData(item) {
  const used = Number(item?.used) || 0;
  const limit = Number(item?.limit) || 0;
  return [['已使用', used], ['可使用', Math.max(limit - used, 0)]];
}

function groupChartData(group) {
  const used = Number(group.used) || 0;
  const limit = Number(group.limit) || 0;
  return [[used], [Math.max(limit - used, 0)]];
}
</script>

<template>
  <div class="dashboard-page">
    <div class="dashboard-card dashboard-filter">
      <ProjectSelect
        v-model="projectId"
        clearable />
    </div>
    <div
      v-if="project"
      class="dashboard-card capacity-card">
      <PieCharts
        :data="capacityData(project)"
        :title="`${project.name} · 项目总览`"
        width="100%"
        height="280px" />
    </div>
    <div
      v-if="groups.length"
      class="dashboard-grid">
      <BarStackChart
        v-for="group in groups"
        :key="group.id"
        class="dashboard-card group-chart"
        :series-names="['used', 'available']"
        :data="groupChartData(group)"
        :categories="[group.name]"
        :series-map="{ used: '已使用(GB)', available: '可使用(GB)' }"
        :title="`${group.group_tag?.name || '未设置标签'} · ${group.name}`"
        width="100%"
        height="100%" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
@import '@/styles/mixins.scss';
.dashboard-page { display: grid; gap: var(--spacing-xl); }
.dashboard-card { @include card-base; border: 1px solid var(--border-color); padding: var(--spacing-lg); }
.dashboard-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--spacing-lg); }
.group-chart { height: 700px; }
@include mobile { .dashboard-grid { grid-template-columns: 1fr; } }
</style>
