<script setup>
import { ElMessage } from 'element-plus';
import { ref, watch } from 'vue';
import DiskUsage from '@/common/charts/DiskUsage.vue';
import aggregateApi from '@/api/aggregate-api.js';

const props = defineProps({
  clusterId: { type: Number, required: true },
});

const storageDistribution = ref({ data: [] });
const loading = ref(false);

async function load() {
  if (!props.clusterId) return;
  loading.value = true;
  try {
    const response = await aggregateApi.fetchAggregateTrees({
      storage_cluster_id: props.clusterId,
    });
    storageDistribution.value = response || { data: [] };
  } catch {
    storageDistribution.value = { data: [] };
    ElMessage.error('加载存储分布失败，请稍后重试');
  } finally {
    loading.value = false;
  }
}

watch(() => props.clusterId, load, { immediate: true });
</script>

<template>
  <section class="cluster-distribution-tab">
    <div
      v-loading="loading"
      class="analytics-chart-stage"
      :aria-busy="loading">
      <div
        v-if="!loading && !storageDistribution.data?.length"
        class="analytics-empty">暂无存储分布数据</div>
      <DiskUsage
        v-else-if="storageDistribution.data?.length"
        :data="storageDistribution.data"
        title=""
        width="100%"
        height="100%" />
    </div>
  </section>
</template>

<style scoped>
.cluster-distribution-tab {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.analytics-chart-stage {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
  position: relative;
}

.analytics-empty {
  display: grid;
  min-height: 360px;
  place-items: center;
  color: var(--el-text-color-secondary);
}
</style>
