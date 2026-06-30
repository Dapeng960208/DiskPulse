<script setup>
import { ElRow,ElCol,ElDescriptions,ElDescriptionsItem,ElCard } from 'element-plus';
import { ref,onBeforeMount,watch} from 'vue';
import projectApi from '@/api/project-api.js';
import { useQuery, useQueryParams } from '@/composables/query';
import StoragePieAndLine from '@/common/charts/StoragePieAndLineCharts.vue';
import BarStackChart from '@/common/charts/BarStackChart.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import PieCharts from '@/common/charts/PieCharts.vue';
const updatedAt = ref('');
function markUpdatedAt() {
  updatedAt.value = new Date().toLocaleString('zh-CN', { hour12: false });
}
const { result:storageSummary, querying:storageSummaryQuerying, query:fetchStorageSummary } = useQuery(() => projectApi.fetchStorageSummary().then((result) => {
  markUpdatedAt();
  return result;
}), {
  data: [],
  tree:[]
});
const { result:groupStorages, querying:groupStorageQuerying, query:fetchGroupStorage } = useQuery(() => projectApi.fetchGroupStorage().then((result) => {
  markUpdatedAt();
  return result;
}), {
  data: []
});
fetchStorageSummary();
fetchGroupStorage();
function transferData(data) {
  if (data.length===0) {
    return [];
  }
  const columnNames = data[0].slice(1);
  const sums = Array(columnNames.length).fill(0);
  for (let i = 1; i < data.length; i++) {
    for (let j = 1; j < data[i].length; j++) {
      sums[j - 1] += data[i][j]; // 累加每列的值
    }
  }
  const finalResult = [];
  for (let i = 0; i < columnNames.length; i++) {
    finalResult.push([columnNames[i], sums[i]]);
  }
  return finalResult;
}

</script>

<template>
  <section class="dashboard-page-header">
    <div>
      <h1>存储监控概览</h1>
      <p>展示项目组容量趋势、当前占比和分组使用情况。</p>
    </div>
    <span v-if="updatedAt">最近刷新：{{ updatedAt }}</span>
  </section>
  <!-- 项目组使用情况 柱状堆叠图 -->
  <ElRow
    v-if="storageSummaryQuerying"
    class="mb-5">
    <ElCol
      :span="24"
      class="h-175 mb-2.5">
      <LoadingCharts
        :width="'100%'"
        :height="'100%'"></LoadingCharts>
    </ElCol>
  </ElRow>
  <ElRow
    v-else
    class="mb-5"
    :gutter="20">
    <ElCol
      v-if="storageSummary.data"
      :span="16"
      class="h-175 mb-2.5">
      <ElCard class="h-full">
        <StoragePieAndLine
          :data="storageSummary.data"
          :y-axis-unit="'T'"
          :height="'100%'"
          :title="''"></StoragePieAndLine>
      </ElCard>
    </ElCol>
    <ElCol
      v-if="storageSummary.data"
      :span="8"
      class="h-175 mb-2.5">
      <ElCard class="h-full ">
        <PieCharts
          :data="transferData(storageSummary.data)"
          :y-axis-unit="'T'"
          :height="'100%'"
          :title="''"></PieCharts>
      </ElCard>
    </ElCol>
  </ElRow>

  <ElRow
    v-if="groupStorageQuerying"
    class="mb-5">
    <ElCol
      :span="24"
      class="h-175 mb-2.5">
      <LoadingCharts
        :width="'100%'"
        :height="'100%'"></LoadingCharts>
    </ElCol>
  </ElRow>
  <ElRow
    v-else
    class="mb-5"
    :gutter="20">
    <ElCol
      v-for="(value,key) in groupStorages.data"
      :key="key"
      :span="8"
      class="h-175 mb-2.5">
      <ElCard class="h-full">
        <BarStackChart
          :series-names="value['series']"
          :data="value['data']"
          :categories="value['categories']"
          :series-map="{'used':'已使用(GB)','available':'可使用(GB)'}"
          :title="key"
          :width="'100%'"
          :height="'100%'"></BarStackChart>
      </ElCard>
    </ElCol>
  </ElRow>

  <!-- 项目组使用占比情况 饼状折线图 -->
  <!-- <ElRow class="mb-5" v-if="storageSummaryQuerying">
    <ElCol :span="24" class="h-350">
        <LoadingCharts :width="'100%'" :height="'600px'"></LoadingCharts>
    </ElCol>
  </ElRow>
  <ElRow  v-else class="mb-5" :gutter="20" >
    <ElCol v-if="storageSummary.data" :span="16">
        <ElCard>
          <StoragePieAndLine :data="storageSummary.data" :y-axis-unit="'T'" :height="'600px'" :title="''"></StoragePieAndLine>
        </ElCard>
    </ElCol>
    <ElCol v-if="storageSummary.data" :span="8">
        <ElCard>
          <PieCharts :data="transferData(storageSummary.data)" :y-axis-unit="'T'" :height="'600px'" :title="''"></PieCharts>
        </ElCard>
    </ElCol>
  </ElRow> -->
</template>
<style lang="scss" scoped>
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';

.dashboard-page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);

  h1 {
    font-size: var(--font-size-2xl);
    color: var(--text-primary);
    margin-bottom: var(--spacing-xs);
  }

  p,
  span {
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
  }

  span {
    white-space: nowrap;
  }
}

:deep(.el-card) {
  @include card-base;
  border: 1px solid var(--border-color);
  transition: var(--transition-all);

  &:hover {
    @include card-hover;
    border-color: var(--border-dark);
  }

  .el-card__body {
    height: 100%;
    padding: var(--spacing-lg);
  }
}

:deep(.el-row) {
  margin-bottom: var(--spacing-xl);
}

:deep(.el-col) {
  animation: slideInUp 0.4s ease-out;
  animation-fill-mode: both;

  &:nth-child(1) { animation-delay: 0.05s; }
  &:nth-child(2) { animation-delay: 0.1s; }
  &:nth-child(3) { animation-delay: 0.15s; }
  &:nth-child(4) { animation-delay: 0.2s; }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@include mobile {
  .dashboard-page-header {
    flex-direction: column;
  }
}
</style>

