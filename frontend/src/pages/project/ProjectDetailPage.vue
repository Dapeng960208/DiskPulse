<script setup>
import {
  ElDescriptions,
  ElDescriptionsItem,
  ElEmpty,
  ElMessage,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
} from 'element-plus';
import { computed, defineAsyncComponent, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import groupApi from '@/api/group-api.js';
import projectStorageEnvironmentApi from '@/api/project-storage-environment-api';
import RealTimePage from '@/pages/common/RealTimePage.vue';

const ProjectStorageEnvironmentTable = defineAsyncComponent(
  () => import('./components/ProjectStorageEnvironmentTable.vue'),
);
const route = useRoute();
const router = useRouter();
const projectId = computed(() => Number(route.params?.id));
const environments = ref([]);
const selectedEnvironmentId = ref(null);
const environmentSummary = ref(null);
const environmentGroups = ref([]);
const loadingEnvironments = ref(false);
const loadingWorkspace = ref(false);
const activeEnvironments = computed(() => environments.value.filter(
  (environment) => environment.is_active,
));

function replaceEnvironmentQuery(environmentId) {
  const query = { ...route.query };
  if (environmentId == null) {
    delete query.environment_id;
  } else {
    query.environment_id = String(environmentId);
  }
  return router.replace({ query });
}

async function loadWorkspace(environmentId) {
  environmentSummary.value = null;
  environmentGroups.value = [];
  loadingWorkspace.value = true;
  try {
    const [summary, groups] = await Promise.all([
      projectStorageEnvironmentApi.fetchSummaryById(environmentId),
      groupApi.fetch({
        project_environment_id: environmentId,
        page: 1,
        size: 100,
      }),
    ]);
    if (selectedEnvironmentId.value !== environmentId) return;
    environmentSummary.value = summary;
    environmentGroups.value = groups.content;
  } catch {
    ElMessage.error('加载存储环境工作台失败，请稍后重试');
  } finally {
    loadingWorkspace.value = false;
  }
}

async function selectEnvironment(environmentId, normalizeUrl = true) {
  const normalizedId = Number(environmentId);
  if (!activeEnvironments.value.some((environment) => environment.id === normalizedId)) return;
  selectedEnvironmentId.value = normalizedId;
  if (normalizeUrl) await replaceEnvironmentQuery(normalizedId);
  await loadWorkspace(normalizedId);
}

async function loadEnvironments() {
  loadingEnvironments.value = true;
  try {
    const result = await projectStorageEnvironmentApi.fetchByProject(projectId.value, {
      page: 1,
      size: 100,
    });
    environments.value = result.content;
    const queryId = Number(route.query.environment_id);
    const selected = activeEnvironments.value.find((environment) => environment.id === queryId);
    const fallback = activeEnvironments.value[0];
    if (!fallback) {
      selectedEnvironmentId.value = null;
      environmentSummary.value = null;
      environmentGroups.value = [];
      if (route.query.environment_id != null) await replaceEnvironmentQuery(null);
      return;
    }
    if (selected) {
      await selectEnvironment(selected.id, false);
    } else {
      await selectEnvironment(fallback.id);
    }
  } catch {
    environments.value = [];
    selectedEnvironmentId.value = null;
    ElMessage.error('加载项目存储环境失败，请稍后重试');
  } finally {
    loadingEnvironments.value = false;
  }
}

onMounted(loadEnvironments);
</script>

<template>
  <div class="project-detail-page">
    <ElTabs
      v-if="activeEnvironments.length"
      :model-value="selectedEnvironmentId"
      @update:model-value="selectEnvironment">
      <ElTabPane
        v-for="environment in activeEnvironments"
        :key="environment.id"
        :label="environment.name"
        :name="environment.id" />
    </ElTabs>

    <ElEmpty
      v-if="!loadingEnvironments && !activeEnvironments.length"
      description="暂无启用的存储环境" />

    <template v-if="selectedEnvironmentId">
      <ElDescriptions
        :column="4"
        border>
        <ElDescriptionsItem label="存储环境">
          {{ environmentSummary?.name || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="存储集群">
          {{ environmentSummary?.storage_cluster?.name || '-' }}
          <ElTag type="info">
            {{ environmentSummary?.storage_cluster?.storage_type || '-' }}
          </ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="使用量">
          {{ environmentSummary?.used ?? '-' }} G
        </ElDescriptionsItem>
        <ElDescriptionsItem label="限额">
          {{ environmentSummary?.limit ?? '-' }} G
        </ElDescriptionsItem>
      </ElDescriptions>

      <RealTimePage
        :attribute-id="selectedEnvironmentId"
        api-type="project-environment"
        label="存储环境" />

      <section class="mt-5">
        <h2 class="mb-3 text-lg font-semibold">
          关联项目组
        </h2>
        <ElTable
          :data="environmentGroups"
          :loading="loadingWorkspace">
          <ElTableColumn
            label="项目组"
            prop="name" />
          <ElTableColumn
            label="Linux 路径"
            prop="linux_path" />
          <ElTableColumn label="存储目标">
            <template #default="{ row }">
              {{ row.storage_target?.type }} / {{ row.storage_target?.name || '-' }}
            </template>
          </ElTableColumn>
        </ElTable>
      </section>
    </template>

    <section class="mt-5">
      <h2 class="mb-3 text-lg font-semibold">
        存储环境配置
      </h2>
      <ProjectStorageEnvironmentTable
        v-if="projectId"
        :project-id="projectId" />
    </section>
  </div>
</template>
