<script setup>
import {
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElMessage,
  ElTabPane,
  ElTabs,
} from 'element-plus';
import { defineAsyncComponent, onBeforeMount, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import storageClusterApi from '@/api/storage-cluster-api';
import { useQuery } from '@/composables/query';
import { getDefaultTime } from '@/composables/common';
import { useBreadcrumbs } from '@/stores/breadcrumbs';
const ClusterCapacityTab = defineAsyncComponent(() => import('./components/ClusterCapacityTab.vue'));
const ClusterDistributionTab = defineAsyncComponent(() => import('./components/ClusterDistributionTab.vue'));
const ClusterPerformanceTab = defineAsyncComponent(() => import('./components/ClusterPerformanceTab.vue'));
const ClusterFaultsTab = defineAsyncComponent(() => import('./components/ClusterFaultsTab.vue'));
const ClusterIncidentsTab = defineAsyncComponent(() => import('./components/ClusterIncidentsTab.vue'));
const ClusterResourceListTab = defineAsyncComponent(() => import('./components/ClusterResourceListTab.vue'));
const CapacityExhaustionRiskPanel = defineAsyncComponent(() => import('@/pages/capacity-prediction/CapacityExhaustionRiskPanel.vue'));

const route = useRoute();
const breadcrumbs = useBreadcrumbs();
const clusterId = ref(null);
const dateRange = ref(getDefaultTime(8));
const activeTab = ref('capacity');
const systemEventDetail = ref(null);
const systemEventDetailVisible = ref(false);
const loading = ref(false);

function hasReviewedVendorSemantics(event) {
  return event?.review_status === 'reviewed'
    && Boolean(event?.association_type)
    && event.association_type !== 'unknown';
}

function vendorEventTitle(event) {
  if (!hasReviewedVendorSemantics(event)) return '待审核 · 未分类厂商事件';
  return event.title_zh || '未收录的厂商事件代码';
}

function vendorEventAssociationLabel(event) {
  if (!hasReviewedVendorSemantics(event)) return '未分类厂商事件';
  return event.association_type_label || '未分类厂商事件';
}

function vendorEventDescription(event) {
  if (!hasReviewedVendorSemantics(event)) {
    return '该事件代码尚未完成审核，不能根据候选定义推断系统问题；请结合规范化日志和厂商文档核查。';
  }
  return event.description_zh || '该代码尚未维护中文说明，请结合规范化日志核查。';
}

function vendorEventRecommendedSolution(event) {
  if (!hasReviewedVendorSemantics(event)) return '暂无可核验官方方案';
  return event.recommended_solution_zh || '暂无可核验官方方案';
}

function vendorEventReviewLabel(event) {
  return hasReviewedVendorSemantics(event) ? '已审核' : '待审核';
}

const fetchClusterInfo = async () => {
  if (!clusterId.value) return {};
  return storageClusterApi.fetchById(clusterId.value);
};
const { result: infoResult, query: queryInfo } = useQuery(fetchClusterInfo, {});
watch(() => infoResult.value?.name, (name) => {
  breadcrumbs.setDetailTitle(route.name, name);
}, { immediate: true });

async function openSystemEventDetail(row) {
  const eventId = row?.sample_event_id || row?.id;
  if (!clusterId.value || !eventId) return;
  loading.value = true;
  systemEventDetailVisible.value = true;
  systemEventDetail.value = null;
  try {
    systemEventDetail.value = await storageClusterApi.fetchSystemEventDetail(
      clusterId.value,
      eventId,
    );
  } catch {
    systemEventDetailVisible.value = false;
    ElMessage.error('加载厂商事件日志失败，请稍后重试');
  } finally {
    loading.value = false;
  }
}

watch(clusterId, () => {
  queryInfo();
});

onBeforeMount(() => {
  const routeClusterId = Number.parseInt(route.params?.id, 10);
  if (Number.isInteger(routeClusterId)) clusterId.value = routeClusterId;
});
</script>

<template>
  <div class="storage-health-page flex flex-col flex-1 min-h-0">
    <ElCard
      v-if="clusterId"
      class="storage-health-page__card">
      <ElTabs
        v-model="activeTab"
        class="storage-health-page__tabs">
        <ElTabPane
          label="容量趋势"
          name="capacity">
          <ClusterCapacityTab
            v-if="activeTab === 'capacity' && clusterId"
            v-model:date-range="dateRange"
            :cluster-id="clusterId"
            :cluster-name="infoResult?.name" />
        </ElTabPane>

        <ElTabPane
          label="存储分布"
          name="distribution">
          <ClusterDistributionTab
            v-if="activeTab === 'distribution' && clusterId"
            :cluster-id="clusterId" />
        </ElTabPane>

        <ElTabPane
          label="容量池"
          name="aggregates">
          <ClusterResourceListTab
            v-if="activeTab === 'aggregates' && clusterId"
            :cluster-id="clusterId"
            resource-type="aggregate" />
        </ElTabPane>

        <ElTabPane
          label="存储空间"
          name="volumes">
          <ClusterResourceListTab
            v-if="activeTab === 'volumes' && clusterId"
            :cluster-id="clusterId"
            resource-type="volume" />
        </ElTabPane>

        <ElTabPane
          v-if="infoResult?.storage_type && infoResult?.storage_type !== 'isilon'"
          label="Qtree（NetApp）"
          name="qtrees">
          <ClusterResourceListTab
            v-if="activeTab === 'qtrees' && clusterId"
            :cluster-id="clusterId"
            resource-type="qtree" />
        </ElTabPane>

        <ElTabPane
          label="性能分析"
          name="performance">
          <ClusterPerformanceTab
            v-if="activeTab === 'performance' && clusterId"
            v-model:date-range="dateRange"
            :cluster-id="clusterId" />
        </ElTabPane>

        <ElTabPane
          label="故障分析"
          name="faults">
          <ClusterFaultsTab
            v-if="activeTab === 'faults' && clusterId"
            v-model:date-range="dateRange"
            :cluster-id="clusterId"
            @open-system-event-detail="openSystemEventDetail" />
        </ElTabPane>
        <ElTabPane
          label="耗尽风险"
          name="exhaustion-risk"
          lazy>
          <CapacityExhaustionRiskPanel
            asset-type="storage_cluster"
            :asset-id="clusterId" />
        </ElTabPane>
        <ElTabPane
          label="关联事件"
          name="incidents">
          <ClusterIncidentsTab
            v-if="activeTab === 'incidents' && clusterId"
            :cluster-id="clusterId" />
        </ElTabPane>
      </ElTabs>
    </ElCard>
    <ElDialog
      v-model="systemEventDetailVisible"
      title="事件日志详情"
      width="min(720px, 96vw)">
      <div
        v-loading="loading"
        class="system-event-detail">
        <ElDescriptions
          v-if="systemEventDetail"
          :column="2"
          border>
          <ElDescriptionsItem label="存储类型">{{ systemEventDetail.source || '-' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="关联类型">{{ vendorEventAssociationLabel(systemEventDetail) }}</ElDescriptionsItem>
          <ElDescriptionsItem label="事件代码">{{ systemEventDetail.event_code || '-' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="审核状态">{{ vendorEventReviewLabel(systemEventDetail) }}</ElDescriptionsItem>
          <ElDescriptionsItem label="中文含义">{{ vendorEventTitle(systemEventDetail) }}</ElDescriptionsItem>
          <ElDescriptionsItem label="事件对象">{{ systemEventDetail.object_name || systemEventDetail.object_id || '集群' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="发生时间">{{ systemEventDetail.occurred_at || '-' }}</ElDescriptionsItem>
          <ElDescriptionsItem
            label="规范化日志"
            :span="2"><pre>{{ systemEventDetail.description || '-' }}</pre></ElDescriptionsItem>
          <ElDescriptionsItem
            label="中文说明"
            :span="2">{{ vendorEventDescription(systemEventDetail) }}</ElDescriptionsItem>
          <ElDescriptionsItem
            label="推荐解决方案"
            :span="2">{{ vendorEventRecommendedSolution(systemEventDetail) }}</ElDescriptionsItem>
        </ElDescriptions>
        <details v-if="systemEventDetail?.fingerprint">
          <summary>技术关联信息</summary>
          <code>{{ systemEventDetail.fingerprint }}</code>
        </details>
      </div>
    </ElDialog>
  </div>
</template>

<style lang="scss" scoped>
/* Hallmark · pre-emit critique: P5 H5 E5 S5 R5 V4 · genre: modern-minimal · macrostructure: Workbench · tone: technical · anchor hue: existing blue */
.storage-health-page {
  overflow-x: hidden;
}

.storage-health-page__card {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.system-event-detail {
  display: grid;
  gap: var(--spacing-sm);
  min-height: 120px;
}

.system-event-detail pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: var(--font-size-sm);
}

.system-event-detail details {
  color: var(--text-secondary);
}

.system-event-detail code {
  display: block;
  margin-top: var(--spacing-xs);
  overflow-wrap: anywhere;
}

.storage-health-page__card :deep(.el-card__body) {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.storage-health-page__tabs {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.storage-health-page__tabs :deep(.el-tabs__header) {
  flex: 0 0 auto;
}

.storage-health-page__tabs :deep(.el-tabs__content) {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

.storage-health-page__tabs :deep(.el-tab-pane) {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  min-width: 0;
  width: 100%;
}
</style>
