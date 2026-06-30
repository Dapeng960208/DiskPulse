<script setup>
import { ElFormItem,ElSelect,ElOption, ElCard } from 'element-plus';
import { onBeforeMount,nextTick} from 'vue';
import projectApi from '@/api/project-api.js';
import { useQuery, useQueryParams } from '@/composables/query';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import DiskUsage from '@/common/charts/DiskUsage.vue';
import FilterForm from '@/components/form/QueryForm.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import AnimatedTextChart from '@/common/charts/AnimatedTextChart.vue'
const props = defineProps({
  attributeId: {
    type: Number,
    required: true,
  },
});
const { queryParams, reset } = useQueryParams(() => ({
  project_id: null,
  value_type:'limit',
}));
const indicatorOption={
    'used': '使用量',
    'limit': '限额',
};
const { result:storageSummary, querying, query:fetchStorageSummary } = useQuery(() => projectApi.fetchStorageTreeById(queryParams.value.project_id,{'value_type':queryParams.value.value_type}), {
  data: []
});
onBeforeMount(() => {
  nextTick(() => {
    queryParams.value.project_id = props.attributeId ? props.attributeId:1;
    fetchStorageSummary();
  });
});

</script>

<template>
  <FilterForm
    @query="{
      fetchStorageSummary();
    }"
    @reset="{
      reset();
      fetchStorageSummary();
    }"
  >
    <ElFormItem label="项目名">
      <ProjectSelect
        v-model="queryParams.project_id"
        placeholder="根据项目名搜索" />
    </ElFormItem>
    <ElFormItem
      label="指标"
      class="ml-80 w-100">
      <ElSelect
        v-model="queryParams.value_type"
        collapse-tags
        collapse-tags-tooltip>
        <ElOption
          v-for="key,value in indicatorOption"
          :key="value"
          :label="key"
          :value="value"
        >
        </ElOption>
      </ElSelect>
    </ElFormItem>
  </FilterForm>
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
