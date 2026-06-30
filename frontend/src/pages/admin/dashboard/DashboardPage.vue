<script setup>
import { ElRow,ElCol,ElDescriptions,ElDescriptionsItem } from 'element-plus';
import { ref,onBeforeMount,watch} from 'vue';
import aggregateApi from '@/api/aggregate-api.js';
import { useQuery, useQueryParams } from '@/composables/query';
import DiskUsage from '@/common/charts/DiskUsage.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import AnimatedTextChart from '@/common/charts/AnimatedTextChart.vue'
const { result:storageSummary, querying:storageSummaryQuerying, query:fetchStorageSummary } = useQuery(() => aggregateApi.fetchAggregateTrees({}), {
  data: [],
});
onBeforeMount(() => {
  fetchStorageSummary();
});

</script>

<template>
  <div class="flex flex-1 flex-col mt-2.5">
    <ElCard class="h-full">
      <div
        v-if="querying"
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
