<script setup>
import { ElButton, ElDescriptionsItem } from 'element-plus';
import { defineAsyncComponent, onBeforeMount, ref } from 'vue';
import RealTimePage from '@/pages/common/RealTimePage.vue';
import capacityPredictionApi from '@/api/capacity-prediction-api.js';
import { useRoute } from 'vue-router';
import { formatStorageTargetType } from '@/utils/storage-resource';
const route = useRoute();
const attributeId = ref(null);
const predictionVisible = ref(false);
const canManagePlans = ref(false);
const activeView = ref('realtime');
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
  <section class="detail-monitor-page">
    <template v-if="activeView === 'realtime'">
      <div
        v-if="predictionVisible"
        class="detail-monitor-page__actions flex justify-end mb-4">
        <ElButton
          data-testid="capacity-prediction-entry"
          type="primary"
          @click="activeView = 'prediction'">容量预测</ElButton>
      </div>
      <RealTimePage
        :attribute-id="attributeId"
        :api-type="'group'"
        :label="'项目组'"
        :show-header="false">
        <template #extra-descriptions="{ info }">
          <ElDescriptionsItem label="项目路径">{{ info?.linux_path }}</ElDescriptionsItem>
          <ElDescriptionsItem label="归属项目">{{ info?.project?.name }}</ElDescriptionsItem>
          <ElDescriptionsItem label="存储目标">{{ formatStorageTargetType(info?.storage_target?.type) }} / {{ info?.storage_target?.name || '-' }}</ElDescriptionsItem>
          <ElDescriptionsItem
            v-if="false"
            label="备份路径">{{ info?.back_path }}</ElDescriptionsItem>
        </template>
      </RealTimePage>
    </template>
    <template v-else>
      <div class="mb-4">
        <ElButton @click="activeView = 'realtime'">返回实时监控</ElButton>
      </div>
      <CapacityPredictionPanel
        asset-type="group"
        :asset-id="attributeId"
        :visible="predictionVisible"
        :can-manage-plans="canManagePlans" />
    </template>
  </section>
</template>
