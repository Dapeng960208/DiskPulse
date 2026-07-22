<script setup>
import { ElDescriptionsItem, ElTabPane, ElTabs } from 'element-plus';
import { defineAsyncComponent, onBeforeMount, ref } from 'vue';
import RealTimePage from '@/pages/common/RealTimePage.vue';
import { useRoute } from 'vue-router';
import { formatStorageTargetType } from '@/utils/storage-resource';
import groupApi from '@/api/group-api.js';
import capacityPredictionApi from '@/api/capacity-prediction-api.js';
import { useBreadcrumbs } from '@/stores/breadcrumbs';
const CapacityExhaustionRiskPanel = defineAsyncComponent(() => import('@/pages/capacity-prediction/CapacityExhaustionRiskPanel.vue'));
const route = useRoute();
const breadcrumbs = useBreadcrumbs();
const attributeId = ref(null);
const activeTab = ref('realtime');
const riskVisible = ref(false);
const riskVisibilityChecked = ref(false);

async function loadProjectBreadcrumb() {
  try {
    const group = await groupApi.fetchById(attributeId.value);
    const projectName = group?.project?.name;
    const groupName = group?.name;
    breadcrumbs.setDetailBreadcrumb(
      route.name,
      projectName && groupName ? ['项目', projectName, `${groupName}项目组详情`] : [],
    );
  } catch {
    breadcrumbs.setDetailBreadcrumb(route.name, []);
  }
}

async function loadRiskVisibility() {
  try {
    riskVisible.value = (await capacityPredictionApi.visibility()).visible === true;
  } catch {
    riskVisible.value = false;
  } finally {
    riskVisibilityChecked.value = true;
  }
}

onBeforeMount(() => {
  attributeId.value = parseInt(route.params?.id);
  breadcrumbs.setDetailBreadcrumb(route.name, []);
  loadProjectBreadcrumb();
  loadRiskVisibility();
});

</script>

<template>
  <section class="detail-monitor-page">
    <ElTabs
      v-model="activeTab"
      class="detail-monitor-page__content">
      <ElTabPane
        label="容量趋势"
        name="realtime">
        <RealTimePage
          class="detail-monitor-page__content"
          :attribute-id="attributeId"
          :api-type="'group'"
          :label="'项目组'"
          :show-header="false"
          :fill-content="true">
          <template #extra-descriptions="{ info }">
            <ElDescriptionsItem label="项目路径">{{ info?.linux_path }}</ElDescriptionsItem>
            <ElDescriptionsItem label="归属项目">{{ info?.project?.name }}</ElDescriptionsItem>
            <ElDescriptionsItem label="存储目标">{{ formatStorageTargetType(info?.storage_target?.type) }} / {{ info?.storage_target?.name || '-' }}</ElDescriptionsItem>
            <ElDescriptionsItem
              v-if="false"
              label="备份路径">{{ info?.back_path }}</ElDescriptionsItem>
          </template>
        </RealTimePage>
      </ElTabPane>
      <ElTabPane
        v-if="riskVisibilityChecked && riskVisible"
        label="耗尽风险"
        name="exhaustion-risk"
        lazy>
        <CapacityExhaustionRiskPanel
          asset-type="group"
          :asset-id="attributeId" />
      </ElTabPane>
    </ElTabs>
  </section>
</template>

<style scoped>
.detail-monitor-page {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.detail-monitor-page__content {
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
}
</style>
