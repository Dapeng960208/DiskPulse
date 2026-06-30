<script setup>
import {
  ElCard,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElFormItem,
  ElOption,
  ElSelect,
} from 'element-plus';
import { ref, watch, computed, onBeforeMount } from 'vue';
import { useRoute } from 'vue-router';
import FilterForm from '@/components/form/QueryForm.vue';
import LineCharts from '@/common/charts/LineCharts.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import AnimatedTextChart from '@/common/charts/AnimatedTextChart.vue';
import storageClusterApi from '@/api/storage-cluster-api';
import { useQuery, useQueryParams } from '@/composables/query';
import { getDefaultTime } from '@/composables/common';

const route = useRoute();
const clusterId = ref(null);
const clusterInfo = ref({});

const dateRange = ref(getDefaultTime(8));

const shortcuts = [
  { text: '一天内', value: () => getDefaultTime(8) },
  { text: '一周内', value: () => getDefaultTime(24 * 7) },
  { text: '一月内', value: () => getDefaultTime(24 * 30) },
  { text: '三月内', value: () => getDefaultTime(24 * 90) },
];

const { queryParams, reset } = useQueryParams(() => ({
  start_time: dateRange.value[0],
  end_time: dateRange.value[1],
  indicator: 'used',
}));

const indicatorOptions = {
  used: '实时使用量',
  use_ratio: '实时使用率',
};

const yAxisUnit = computed(() => {
  return queryParams.value.indicator === 'used' ? 'G' : '%';
});

const fetchRealtime = async () => {
  if (!clusterId.value) return { data: [] };
  const result = await storageClusterApi.fetchStorageRealTimeDataById(clusterId.value, queryParams.value);
  return result;
};

const { result, querying, query } = useQuery(fetchRealtime, { data: [] });

const fetchClusterInfo = async () => {
  if (!clusterId.value) return {};
  return storageClusterApi.fetchById(clusterId.value);
};

const { result: infoResult, query: queryInfo } = useQuery(fetchClusterInfo, {});

watch(dateRange, (newVal) => {
  queryParams.value.start_time = newVal[0];
  queryParams.value.end_time = newVal[1];
  query();
}, { immediate: false });

watch(() => queryParams.value.indicator, () => {
  query();
});

onBeforeMount(() => {
  clusterId.value = parseInt(route.params?.id);
  queryInfo();
  query();
});
</script>

<template>
  <div class="flex flex-col flex-1 min-h-0">
    <FilterForm
      @query="query()"
      @reset="reset(); query();"
    >
      <ElFormItem
        label="时间范围"
        class="w-120">
        <ElDatePicker
          v-model="dateRange"
          type="datetimerange"
          range-separator="至"
          format="YYYY-MM-DD HH:mm:ss"
          value-format="YYYY-MM-DD HH:mm:ss"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :shortcuts="shortcuts"
        />
      </ElFormItem>
      <ElFormItem
        label="指标"
        class="ml-10 w-60">
        <ElSelect v-model="queryParams.indicator">
          <ElOption
            v-for="(label, value) in indicatorOptions"
            :key="value"
            :label="label"
            :value="value" />
        </ElSelect>
      </ElFormItem>
    </FilterForm>

    <ElCard class="mt-2.5">
      <ElDescriptions
        :column="4"
        size="large"
        border>
        <ElDescriptionsItem label="集群名称">{{ infoResult.name }}</ElDescriptionsItem>
        <ElDescriptionsItem label="描述">{{ infoResult.description }}</ElDescriptionsItem>
        <ElDescriptionsItem label="SSH 端口">{{ infoResult.storage_port }}</ElDescriptionsItem>
        <ElDescriptionsItem label="SSH 用户名">{{ infoResult.storage_user }}</ElDescriptionsItem>
        <ElDescriptionsItem label="创建时间">{{ infoResult.created_at }}</ElDescriptionsItem>
        <ElDescriptionsItem label="更新时间">{{ infoResult.updated_at }}</ElDescriptionsItem>
      </ElDescriptions>
    </ElCard>

    <ElCard class="mt-2.5 flex-auto">
      <div
        v-if="querying"
        class="h-full">
        <LoadingCharts
          :width="'100%'"
          :height="'100%'" />
      </div>
      <div
        v-else-if="!result.data || result.data.length === 0"
        class="h-full">
        <AnimatedTextChart
          :text="'NO DATA'"
          :width="'100%'"
          :height="'100%'" />
      </div>
      <div
        v-else
        class="h-full">
        <LineCharts
          :data="result.data"
          :title="''"
          :is-count="false"
          :width="'100%'"
          :height="'100%'"
          :show-stats="true"
          :y-axis-unit="yAxisUnit"
          :legend-name="infoResult.name"
        />
      </div>
    </ElCard>
  </div>
</template>

<style lang="scss" scoped>
:deep(.el-card) {
  .el-card__body {
    height: 100%;
  }
}
</style>
