<script setup>
import { ElCard } from 'element-plus';
import { ref, watch } from 'vue';
import projectApi from '@/api/project-api.js';
import DiskUsage from '@/common/charts/DiskUsage.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import AnimatedTextChart from '@/common/charts/AnimatedTextChart.vue';

const props = defineProps({
  projectId: {
    type: Number,
    required: true,
  },
});

const storageTree = ref([]);
const loading = ref(false);
const error = ref('');

async function loadStorageTree() {
  const projectId = Number(props.projectId);
  if (!Number.isInteger(projectId) || projectId <= 0) {
    storageTree.value = [];
    return;
  }

  loading.value = true;
  error.value = '';
  try {
    const result = await projectApi.fetchStorageTreeById(projectId, { value_type: 'used' });
    storageTree.value = result?.data || [];
  } catch {
    storageTree.value = [];
    error.value = '加载存储分布失败，请稍后重试';
  } finally {
    loading.value = false;
  }
}

watch(() => props.projectId, loadStorageTree, { immediate: true });
</script>

<template>
  <section class="project-storage-distribution">
    <ElCard class="project-storage-distribution__card">
      <LoadingCharts
        v-if="loading"
        width="100%"
        height="100%" />
      <p
        v-else-if="error"
        class="project-storage-distribution__error"
        role="alert">
        {{ error }}
      </p>
      <AnimatedTextChart
        v-else-if="storageTree.length === 0"
        text="暂无存储分布数据"
        width="100%"
        height="100%" />
      <DiskUsage
        v-else
        :data="storageTree"
        title=""
        label="项目组 / 用户存储分布"
        width="100%"
        height="100%" />
    </ElCard>
  </section>
</template>

<style lang="scss" scoped>
.project-storage-distribution {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;

  &__card {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-height: 0;

    :deep(.el-card__body) {
      display: flex;
      flex: 1 1 auto;
      flex-direction: column;
      min-height: 0;
    }
  }

  &__error {
    display: grid;
    flex: 1 1 auto;
    min-height: 0;
    place-items: center;
    margin: 0;
    color: var(--danger-color);
  }
}

@media (max-width: 768px) {
  .project-storage-distribution__card {
    min-height: 320px;
  }
}
</style>
