<script setup>
import { ElDescriptionsItem, ElTabPane, ElTabs } from 'element-plus';
import { defineAsyncComponent, onBeforeMount, ref } from 'vue';
import RealTimePage from '@/pages/common/RealTimePage.vue';
import capacityPredictionApi from '@/api/capacity-prediction-api.js';
import { useRoute } from 'vue-router';
import { formatStorageTargetType } from '@/utils/storage-resource';
const route = useRoute();
const attributeId = ref(null);
const predictionVisible = ref(false);
const canManagePlans = ref(false);
const CapacityPredictionPanel = defineAsyncComponent(() => import('@/pages/capacity-prediction/CapacityPredictionPanel.vue'));
onBeforeMount(() => {
  attributeId.value = parseInt(route.params?.id);
  capacityPredictionApi.access('group', attributeId.value).then((value) => {
    predictionVisible.value = value.visible === true;
    canManagePlans.value = value.can_manage_plans === true;
  }).catch(() => { predictionVisible.value = false; canManagePlans.value = false; });
});

</script>

<template>
  <ElTabs>
    <ElTabPane label="实时监控"><RealTimePage
      :attribute-id="attributeId"
      :api-type="'group'"
      :label="'项目组'"><template #extra-descriptions="{ info }"><ElDescriptionsItem label="项目路径">{{ info?.linux_path }}</ElDescriptionsItem><ElDescriptionsItem label="归属项目">{{ info?.project?.name }}</ElDescriptionsItem><ElDescriptionsItem label="存储目标">{{ formatStorageTargetType(info?.storage_target?.type) }} / {{ info?.storage_target?.name || '-' }}</ElDescriptionsItem><ElDescriptionsItem
        v-if="false"
        label="备份路径">{{ info?.back_path }}</ElDescriptionsItem></template></RealTimePage></ElTabPane>
    <ElTabPane
      v-if="predictionVisible"
      lazy
      label="容量预测"><CapacityPredictionPanel
        asset-type="group"
        :asset-id="attributeId"
        :visible="predictionVisible"
        :can-manage-plans="canManagePlans" /></ElTabPane>
  </ElTabs>

</template>
