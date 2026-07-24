<script setup>
import {
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElFormItem,
  ElMessage,
} from 'element-plus';
import { computed, ref, watch } from 'vue';
import FilterForm from '@/components/form/QueryForm.vue';
import TimeRangePicker from '@/components/form/TimeRangePicker.vue';
import StorageTrendChart from '@/components/dashboard/StorageTrendChart.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import storageClusterApi from '@/api/storage-cluster-api';
import { formatCapacity } from '@/utils/capacity';
import { toUtcRange } from '@/utils/datetime.js';
import { useClusterExport } from '@/composables/useClusterExport';

const props = defineProps({
  clusterId: { type: Number, required: true },
  clusterName: { type: String, default: '' },
  dateRange: { type: Array, required: true },
});

const emit = defineEmits(['update:dateRange']);

const localDateRange = computed({
  get: () => props.dateRange,
  set: (value) => emit('update:dateRange', value),
});

const capacity = ref({ data: [] });
const loading = ref(false);

const capacityData = computed(() => capacity.value?.data || []);
const capacityChartData = computed(() => capacityData.value.map((item) => [item.updated_at, Number(item.used)]));
const capacityUnit = computed(() => capacity.value?.data_unit || 'TB');
const capacityLabel = (field) => formatCapacity(capacity.value?.capacity?.[field]);
const capacitySeries = computed(() => [{
  name: props.clusterName || '已使用',
  data: capacityChartData.value,
}]);

const { handleExport } = useClusterExport({
  clusterId: computed(() => props.clusterId),
  dateRange: localDateRange,
  defaultSection: 'capacity',
});

async function load() {
  if (!props.clusterId) return;
  loading.value = true;
  const [start_time, end_time] = toUtcRange(localDateRange.value);
  try {
    capacity.value = await storageClusterApi.fetchCapacityChange(props.clusterId, {
      start_time,
      end_time,
    });
  } catch {
    capacity.value = { data: [] };
    ElMessage.error('加载容量趋势失败，请稍后重试');
  } finally {
    loading.value = false;
  }
}

function search() {
  load();
}

function reset() {
  emit('update:dateRange', props.dateRange);
  load();
}

watch(() => props.clusterId, load, { immediate: true });
watch(() => props.dateRange, load);
</script>

<template>
  <section class="cluster-capacity-tab">
    <FilterForm
      class="capacity-filter"
      @query="search"
      @reset="reset">
      <ElFormItem
        label="时间范围"
        class="analytics-date-range query-form-field--date-range">
        <!-- Storage health analytics endpoints reject ranges over 180 days. -->
        <TimeRangePicker
          v-model="localDateRange"
          :max-days="180" />
      </ElFormItem>
      <template #actions>
        <ElDropdown @command="handleExport">
          <ElButton type="primary">导出报告</ElButton>
          <template #dropdown>
            <ElDropdownMenu>
              <ElDropdownItem command="current:csv">当前页 CSV</ElDropdownItem>
              <ElDropdownItem command="current:excel">当前页 Excel</ElDropdownItem>
              <ElDropdownItem command="current:pdf">当前页 PDF</ElDropdownItem>
              <ElDropdownItem
                divided
                command="all:csv">完整报告 CSV</ElDropdownItem>
              <ElDropdownItem command="all:excel">完整报告 Excel</ElDropdownItem>
              <ElDropdownItem command="all:pdf">完整报告 PDF</ElDropdownItem>
            </ElDropdownMenu>
          </template>
        </ElDropdown>
      </template>
    </FilterForm>
    <LoadingCharts
      v-if="loading"
      width="100%"
      height="520px" />
    <div
      v-else-if="!capacityData.length"
      class="analytics-empty">暂无容量数据</div>
    <div v-else>
      <ElDescriptions
        :column="4"
        border>
        <ElDescriptionsItem label="期初已使用">{{ capacityLabel('start_used') }}</ElDescriptionsItem>
        <ElDescriptionsItem label="期末已使用">{{ capacityLabel('end_used') }}</ElDescriptionsItem>
        <ElDescriptionsItem label="变化量">{{ capacityLabel('change') }}</ElDescriptionsItem>
        <ElDescriptionsItem label="变化率">{{ capacity.change_percent == null ? '-' : `${capacity.change_percent}%` }}</ElDescriptionsItem>
      </ElDescriptions>
      <StorageTrendChart
        :series="capacitySeries"
        indicator="used"
        :trend-meta="capacity.trend_meta"
        aria-label="存储集群已使用容量趋势"
        height="520px"
        :unit="capacityUnit" />
    </div>
  </section>
</template>

<style scoped>
.cluster-capacity-tab {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.capacity-filter {
  margin-bottom: var(--spacing-md);
}

.capacity-filter :deep(.analytics-date-range .el-date-editor) {
  width: 100%;
}

.analytics-empty {
  display: grid;
  min-height: 360px;
  place-items: center;
  color: var(--el-text-color-secondary);
}
</style>
