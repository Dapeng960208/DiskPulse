<script setup>
import { ref, watch } from 'vue';
import aggregateApi from '@/api/aggregate-api.js';
import { useQuery } from '@/composables/query';
import StorageClusterSelect from '@/components/form/StorageClusterSelect.vue';
import DiskUsage from '@/common/charts/DiskUsage.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import AnimatedTextChart from '@/common/charts/AnimatedTextChart.vue'
const storageClusterId = ref(null);
const { result:storageSummary, querying:storageSummaryQuerying, query:fetchStorageSummary } = useQuery(() => aggregateApi.fetchAggregateTrees({
  storage_cluster_id: storageClusterId.value,
}), {
  data: [],
});
watch(storageClusterId, fetchStorageSummary, { immediate: true });

</script>

<template>
  <div class="flex flex-1 flex-col mt-2.5">
    <div class="w-80 mb-4">
      <StorageClusterSelect
        v-model="storageClusterId"
        :clearable="true" />
    </div>
    <ElCard class="flex-1 min-h-0">
      <div
        v-if="storageSummaryQuerying"
        class="h-full">
        <LoadingCharts
          :width="'100%'"
          :height="'100%'" />
      </div>
      <div
        v-else-if="storageSummary.data.length===0"
        class="h-full">
        <AnimatedTextChart
          :text="'NO DATA'"
          :width="'100%'"
          :height="'100%'" />
      </div>
      <div
        v-else
        class="h-full">
        <DiskUsage
          :data="storageSummary.data"
          :title="''"
          :width="'100%'"
          :height="'100%'"></DiskUsage>
      </div>
    </ElCard>
  </div>
</template>
<style scoped>
:deep(.el-card__body) {
  height: 100%;
}
</style>
