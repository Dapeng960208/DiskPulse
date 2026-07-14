<script setup>
import { ElEmpty, ElMessage, ElTable, ElTableColumn, ElTag } from 'element-plus';
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import groupApi from '@/api/group-api.js';

const route = useRoute();
const projectId = computed(() => Number(route.params.id));
const groups = ref([]);
const loading = ref(false);

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

onMounted(loadGroups);
</script>

<template>
  <div class="project-detail-page">
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
      <ElTableColumn label="存储集群"><template #default="scope">{{ scope?.row?.storage_cluster?.name || '-' }} <ElTag type="info">{{ scope?.row?.storage_cluster?.storage_type || '-' }}</ElTag></template></ElTableColumn>
      <ElTableColumn label="存储目标"><template #default="scope">{{ scope?.row?.storage_target?.type || '-' }} / {{ scope?.row?.storage_target?.name || '-' }}</template></ElTableColumn>
      <ElTableColumn
        label="Linux路径"
        prop="linux_path" />
    </ElTable>
  </div>
</template>
