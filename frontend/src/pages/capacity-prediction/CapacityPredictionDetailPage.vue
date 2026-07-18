<script setup>
import { computed, defineAsyncComponent, onMounted, ref } from 'vue';
import { ElButton, ElEmpty } from 'element-plus';
import { useRoute, useRouter } from 'vue-router';
import capacityPredictionApi from '@/api/capacity-prediction-api.js';

const props = defineProps({
  assetType: { type: String, required: true },
  listRouteName: { type: String, required: true },
  listLabel: { type: String, required: true },
});

const route = useRoute();
const router = useRouter();
const assetId = computed(() => Number(route.params.id));
const predictionVisible = ref(false);
const canManagePlans = ref(false);
const accessChecked = ref(false);
const CapacityPredictionPanel = defineAsyncComponent(() => import('./CapacityPredictionPanel.vue'));

async function loadAccess() {
  try {
    const access = await capacityPredictionApi.access(props.assetType, assetId.value);
    predictionVisible.value = access.visible === true;
    canManagePlans.value = access.can_manage_plans === true;
  } catch {
    predictionVisible.value = false;
    canManagePlans.value = false;
  } finally {
    accessChecked.value = true;
  }
}

onMounted(loadAccess);
</script>

<template>
  <section class="capacity-prediction-detail-page">
    <div class="capacity-prediction-detail-page__actions">
      <ElButton @click="router.push({ name: listRouteName })">返回{{ listLabel }}</ElButton>
    </div>
    <CapacityPredictionPanel
      v-if="predictionVisible"
      :asset-type="assetType"
      :asset-id="assetId"
      :visible="predictionVisible"
      :can-manage-plans="canManagePlans" />
    <ElEmpty
      v-else-if="accessChecked"
      description="容量预测未启用或当前资源无访问权限" />
  </section>
</template>

<style scoped>
.capacity-prediction-detail-page { display: grid; gap: var(--spacing-md); }
.capacity-prediction-detail-page__actions { display: flex; justify-content: flex-start; }
</style>
