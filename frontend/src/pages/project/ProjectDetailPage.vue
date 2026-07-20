<script setup>
import { ElTabPane, ElTabs } from 'element-plus';
import { computed, defineAsyncComponent, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import projectApi from '@/api/project-api.js';
import { useBreadcrumbs } from '@/stores/breadcrumbs';

const ProjectMembersTab = defineAsyncComponent(() => import('./components/ProjectMembersTab.vue'));
const ProjectAuditTab = defineAsyncComponent(() => import('./components/ProjectAuditTab.vue'));
const ProjectDiskUsage = defineAsyncComponent(() => import('./components/ProjectDiskUsage.vue'));
const ProjectStorageDistribution = defineAsyncComponent(() => import('./components/ProjectStorageDistribution.vue'));
const ProjectGroupsTab = defineAsyncComponent(() => import('./components/ProjectGroupsTab.vue'));
const ProjectUsagesTab = defineAsyncComponent(() => import('./components/ProjectUsagesTab.vue'));

const route = useRoute();
const breadcrumbs = useBreadcrumbs();
const projectId = computed(() => Number(route.params.id));
const project = ref(null);
const activeTab = ref('realtime');
const canManageMembers = computed(() => project.value?.capabilities?.manage_members === true);
const canViewAuditEvents = computed(() => project.value?.capabilities?.view_audit_events === true);
const canManageProjectAdmins = computed(() => project.value?.capabilities?.manage_project_admins === true);

async function loadProject() {
  try {
    project.value = await projectApi.fetchById(projectId.value);
    const projectName = project.value?.name || '';
    breadcrumbs.setDetailTitle(route.name, projectName);
    breadcrumbs.setDetailBreadcrumb(route.name, projectName ? ['项目', projectName] : []);
  } catch {
    project.value = null;
    breadcrumbs.setDetailTitle(route.name, '');
    breadcrumbs.setDetailBreadcrumb(route.name, []);
  }
}

onMounted(() => {
  breadcrumbs.setDetailTitle(route.name, '');
  breadcrumbs.setDetailBreadcrumb(route.name, []);
  loadProject();
});
</script>

<template>
  <section class="project-detail-page">
    <ElTabs
      v-model="activeTab"
      class="project-detail-page__tabs">
      <ElTabPane
        label="项目使用实时"
        name="realtime"
        class="project-detail-page__visual-tab"
        lazy>
        <ProjectDiskUsage :attribute-id="projectId" />
      </ElTabPane>
      <ElTabPane
        label="存储分布"
        name="distribution"
        class="project-detail-page__visual-tab"
        lazy>
        <ProjectStorageDistribution :project-id="projectId" />
      </ElTabPane>
      <ElTabPane
        class="project-detail-page__table-tab"
        label="项目组"
        name="groups"
        lazy>
        <ProjectGroupsTab :project-id="projectId" />
      </ElTabPane>
      <ElTabPane
        class="project-detail-page__table-tab"
        label="用户目录"
        name="usages"
        lazy>
        <ProjectUsagesTab :project-id="projectId" />
      </ElTabPane>
      <ElTabPane
        v-if="canManageMembers"
        class="project-detail-page__table-tab"
        label="成员与权限"
        name="members">
        <ProjectMembersTab
          :project-id="projectId"
          :can-manage-members="canManageMembers"
          :can-manage-project-admins="canManageProjectAdmins" />
      </ElTabPane>
      <ElTabPane
        v-if="canViewAuditEvents"
        class="project-detail-page__table-tab"
        label="项目审计"
        name="audit">
        <ProjectAuditTab :project-id="projectId" />
      </ElTabPane>
    </ElTabs>
  </section>
</template>

<style scoped>
.project-detail-page {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.project-detail-page__tabs {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

:deep(.project-detail-page__tabs .el-tabs__content) {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

:deep(.project-detail-page__tabs .project-detail-page__visual-tab) {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

:deep(.project-detail-page__tabs .project-detail-page__table-tab) {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}
</style>
