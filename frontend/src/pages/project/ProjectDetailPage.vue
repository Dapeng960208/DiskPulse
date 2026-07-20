<script setup>
import { ElTabPane, ElTabs } from 'element-plus';
import { computed, defineAsyncComponent, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import projectApi from '@/api/project-api.js';
import { useBreadcrumbs } from '@/stores/breadcrumbs';

const ProjectMembersTab = defineAsyncComponent(() => import('./components/ProjectMembersTab.vue'));
const ProjectAuditTab = defineAsyncComponent(() => import('./components/ProjectAuditTab.vue'));
const ProjectDiskUsage = defineAsyncComponent(() => import('./components/ProjectDiskUsage.vue'));
const ProjectGroupsTab = defineAsyncComponent(() => import('./components/ProjectGroupsTab.vue'));
const ProjectUsagesTab = defineAsyncComponent(() => import('./components/ProjectUsagesTab.vue'));

const route = useRoute();
const breadcrumbs = useBreadcrumbs();
const projectId = computed(() => Number(route.params.id));
const project = ref(null);
const activeTab = ref('capacity');
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
    <ElTabs v-model="activeTab">
      <ElTabPane
        label="存储分布"
        name="capacity"
        lazy>
        <ProjectDiskUsage
          :attribute-id="projectId"
          :allow-project-selection="false" />
      </ElTabPane>
      <ElTabPane
        label="项目组"
        name="groups"
        lazy>
        <ProjectGroupsTab :project-id="projectId" />
      </ElTabPane>
      <ElTabPane
        label="用户目录"
        name="usages"
        lazy>
        <ProjectUsagesTab :project-id="projectId" />
      </ElTabPane>
      <ElTabPane
        v-if="canManageMembers"
        label="成员与权限"
        name="members">
        <ProjectMembersTab
          :project-id="projectId"
          :can-manage-members="canManageMembers"
          :can-manage-project-admins="canManageProjectAdmins" />
      </ElTabPane>
      <ElTabPane
        v-if="canViewAuditEvents"
        label="项目审计"
        name="audit">
        <ProjectAuditTab :project-id="projectId" />
      </ElTabPane>
    </ElTabs>
  </section>
</template>
