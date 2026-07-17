<script setup>
import { ElEmpty, ElMessage, ElTable, ElTableColumn, ElTabPane, ElTabs } from 'element-plus';
import { computed, defineAsyncComponent, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import groupApi from '@/api/group-api.js';
import projectApi from '@/api/project-api.js';
import { formatStorageTargetType } from '@/utils/storage-resource';
import StorageTypeTag from '@/components/data/StorageTypeTag.vue';
import { useBreadcrumbs } from '@/stores/breadcrumbs';

const ProjectMembersTab = defineAsyncComponent(() => import('./components/ProjectMembersTab.vue'));
const ProjectAuditTab = defineAsyncComponent(() => import('./components/ProjectAuditTab.vue'));

const route = useRoute();
const breadcrumbs = useBreadcrumbs();
const projectId = computed(() => Number(route.params.id));
const project = ref(null);
const groups = ref([]);
const loading = ref(false);
const activeTab = ref('groups');
const canManageMembers = computed(() => project.value?.capabilities?.manage_members === true);
const canViewAuditEvents = computed(() => project.value?.capabilities?.view_audit_events === true);
const canManageProjectAdmins = computed(() => project.value?.capabilities?.manage_project_admins === true);

async function loadGroups() {
  loading.value = true;
  try {
    const result = await groupApi.fetch({ project_id: projectId.value, page: 1, size: 100 });
    groups.value = result.content;
  } catch {
    groups.value = [];
    ElMessage.error('加载项目组失败，请稍后重试');
  } finally {
    loading.value = false;
  }
}

async function loadProject() {
  try {
    project.value = await projectApi.fetchById(projectId.value);
    breadcrumbs.setDetailTitle(route.name, project.value?.name);
  } catch {
    project.value = null;
    breadcrumbs.setDetailTitle(route.name, '');
  }
}

onMounted(() => {
  breadcrumbs.setDetailTitle(route.name, '');
  loadGroups();
  loadProject();
});
</script>

<template>
  <section class="project-detail-page">
    <ElTabs v-model="activeTab">
      <ElTabPane
        label="项目组"
        name="groups">
        <ElEmpty
          v-if="!loading && !groups.length"
          description="暂无关联项目组" />
        <ElTable
          v-else
          :data="groups"
          :loading="loading">
          <ElTableColumn
            label="项目组"
            prop="name" />
          <ElTableColumn label="项目组标签"><template #default="scope">{{ scope?.row?.group_tag?.name || '-' }}</template></ElTableColumn>
          <ElTableColumn label="存储集群">
            <template #default="scope">
              {{ scope?.row?.storage_cluster?.name || '-' }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="存储类型">
            <template #default="scope">
              <StorageTypeTag :value="scope?.row?.storage_cluster?.storage_type" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="存储目标"><template #default="scope">{{ formatStorageTargetType(scope?.row?.storage_target?.type) }} / {{ scope?.row?.storage_target?.name || '-' }}</template></ElTableColumn>
          <ElTableColumn
            label="Linux路径"
            prop="linux_path" />
        </ElTable>
      </ElTabPane>
      <ElTabPane
        v-if="canManageMembers"
        label="成员"
        name="members">
        <ProjectMembersTab
          :project-id="projectId"
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
