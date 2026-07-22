<script setup>
import { computed, defineAsyncComponent, onMounted, reactive, ref, watch } from 'vue';
import {
  ElEmpty,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';
import { useRoute } from 'vue-router';
import RealTimePage from '@/pages/common/RealTimePage.vue';
import DataTable from '@/components/data/DataTable.vue';
import { useBreadcrumbs } from '@/stores/breadcrumbs';
import storageUsageApi from '@/api/storage-usage-api.js';
import capacityPredictionApi from '@/api/capacity-prediction-api.js';
import { formatQuotaLimit } from '@/utils/quota';
import QuotaAdjustmentDialog from '@/components/form/QuotaAdjustmentDialog.vue';
import TableActionButton from '@/components/basic/TableActionButton.vue';
const CapacityExhaustionRiskPanel = defineAsyncComponent(() => import('@/pages/capacity-prediction/CapacityExhaustionRiskPanel.vue'));

const route = useRoute();
const breadcrumbs = useBreadcrumbs();
const usageId = computed(() => Number(route.params?.id));
const activeTab = ref('capacity');
const usage = ref(null);
const usageLoading = ref(false);
const usageError = ref('');
const riskVisible = ref(false);
const riskVisibilityChecked = ref(false);
const quotaHistory = ref([]);
const incidents = ref([]);
const loaded = reactive({ quotaHistory: false, incidents: false });
const loading = reactive({ quotaHistory: false, incidents: false });
const errors = reactive({ quotaHistory: '', incidents: '' });
const canViewQuotaHistory = computed(() => usage.value?.capabilities?.adjust_quota === true);
const quotaAdjustmentDialogRef = ref();

function statusType(value) {
  if (['success', 'resolved', 'ready'].includes(value)) return 'success';
  if (['failure', 'critical', 'emergency'].includes(value)) return 'danger';
  if (['warning', 'important', 'open'].includes(value)) return 'warning';
  return 'info';
}

function quotaChange(row) {
  const before = formatQuotaLimit(row.before_summary?.hard_limit, { emptyText: '-' });
  const after = formatQuotaLimit(row.after_summary?.hard_limit, { emptyText: '-' });
  return `${before} → ${after}`;
}

async function loadUsage() {
  if (!Number.isInteger(usageId.value) || usageId.value < 1) return;
  usageLoading.value = true;
  usageError.value = '';
  try {
    usage.value = await storageUsageApi.fetchById(usageId.value, undefined, {
      errorHandlerDisabled: true,
    });
    const projectName = usage.value?.project?.name;
    const userName = usage.value?.user?.rd_username
      || usage.value?.user?.username
      || usage.value?.linux_path?.split('/').filter(Boolean).at(-1);
    breadcrumbs.setDetailBreadcrumb(
      route.name,
      projectName && userName ? ['项目', projectName, `${userName}用户详情`] : [],
    );
    await loadActiveTab();
  } catch {
    usage.value = null;
    usageError.value = '加载用户目录详情失败，请稍后重试';
    breadcrumbs.setDetailBreadcrumb(route.name, []);
  } finally {
    usageLoading.value = false;
  }
}

async function loadQuotaHistory() {
  if (loaded.quotaHistory || loading.quotaHistory || !canViewQuotaHistory.value) return;
  loading.quotaHistory = true;
  errors.quotaHistory = '';
  try {
    quotaHistory.value = await storageUsageApi.quotaHistory(usageId.value, {
      errorHandlerDisabled: true,
    });
    loaded.quotaHistory = true;
  } catch {
    quotaHistory.value = [];
    errors.quotaHistory = '加载配额历史失败，请稍后重试';
  } finally {
    loading.quotaHistory = false;
  }
}

function openQuotaAdjustment() {
  quotaAdjustmentDialogRef.value?.open?.(usage.value);
}

async function handleQuotaAdjusted() {
  loaded.quotaHistory = false;
  quotaHistory.value = [];
  await loadUsage();
}

async function loadRiskVisibility() {
  try {
    const result = await capacityPredictionApi.visibility();
    riskVisible.value = result.visible === true;
  } catch {
    riskVisible.value = false;
  } finally {
    riskVisibilityChecked.value = true;
  }
}

async function loadIncidents() {
  if (loaded.incidents || loading.incidents) return;
  loading.incidents = true;
  errors.incidents = '';
  try {
    incidents.value = await capacityPredictionApi.fetchRelatedIncidents('storage_usage', usageId.value, {
      errorHandlerDisabled: true,
    });
    loaded.incidents = true;
  } catch {
    incidents.value = [];
    errors.incidents = '加载关联事件失败，请稍后重试';
  } finally {
    loading.incidents = false;
  }
}

async function loadActiveTab() {
  if (!Number.isInteger(usageId.value) || usageId.value < 1) return;
  if (activeTab.value === 'quota-history') return loadQuotaHistory();
  if (activeTab.value === 'incidents') return loadIncidents();
}

watch(activeTab, loadActiveTab);
onMounted(() => {
  breadcrumbs.setDetailBreadcrumb(route.name, []);
  loadUsage();
  loadRiskVisibility();
});
</script>

<template>
  <section class="usage-detail-page">
    <div
      v-if="canViewQuotaHistory"
      class="usage-detail-page__actions">
      <TableActionButton
        action="edit"
        @click="openQuotaAdjustment">调整额度</TableActionButton>
    </div>
    <ElTabs
      v-model="activeTab"
      class="usage-detail-page__tabs">
      <ElTabPane
        class="usage-detail-page__capacity-tab"
        label="容量趋势"
        name="capacity">
        <RealTimePage
          class="usage-detail-page__realtime-content"
          :attribute-id="usageId"
          api-type="storage-usage"
          label="用户目录"
          :show-header="false"
          :fill-content="true">
          <!-- 暂时隐藏第 2–4 行扩展字段，恢复时移出此注释并补回 ElDescriptionsItem 导入。
          <template #extra-descriptions="{ info }">
            <ElDescriptionsItem label="文件数量">{{ info?.file_used }}</ElDescriptionsItem>
            <ElDescriptionsItem label="目录权限">{{ info?.access }}</ElDescriptionsItem>
            <ElDescriptionsItem label="访问时间(Access Time)">{{ info?.access_time }}</ElDescriptionsItem>
            <ElDescriptionsItem label="修改时间(Modify Time)">{{ info?.modify_time }}</ElDescriptionsItem>
            <ElDescriptionsItem label="改变时间(Change Time)">{{ info?.change_time }}</ElDescriptionsItem>
            <ElDescriptionsItem label="创建时间">{{ info?.resources_content }}</ElDescriptionsItem>
            <ElDescriptionsItem label="权限组">{{ info?.gid }}</ElDescriptionsItem>
            <ElDescriptionsItem label="Inode编号">{{ info?.inode }}</ElDescriptionsItem>
            <ElDescriptionsItem label="硬链接数量">{{ info?.links }}</ElDescriptionsItem>
            <ElDescriptionsItem label="系统的I/O块大小">{{ info?.blocks }}</ElDescriptionsItem>
            <ElDescriptionsItem label="IO块(IO Block)">{{ info?.io_block }}</ElDescriptionsItem>
            <ElDescriptionsItem label="设备的标识号">{{ info?.device }}</ElDescriptionsItem>
          </template>
          -->
        </RealTimePage>
      </ElTabPane>
      <ElTabPane
        label="配额历史"
        name="quota-history"
        lazy>
        <ElEmpty
          v-if="!usageLoading && !canViewQuotaHistory"
          :description="usageError || '当前账号无权查看配额历史'" />
        <DataTable
          v-else
          :data="quotaHistory"
          :loading="loading.quotaHistory"
          :error="errors.quotaHistory">
          <ElTableColumn
            label="时间"
            prop="occurred_at"
            min-width="190" />
          <ElTableColumn
            label="操作"
            min-width="120">
            <template #default="{ row }">{{ row.action === 'quota.reconcile' ? '配额对账' : '配额调整' }}</template>
          </ElTableColumn>
          <ElTableColumn
            label="硬限额变化"
            min-width="180">
            <template #default="{ row }">{{ quotaChange(row) }}</template>
          </ElTableColumn>
          <ElTableColumn
            label="变更原因"
            min-width="180">
            <template #default="{ row }">{{ row.metadata?.change_reason || '-' }}</template>
          </ElTableColumn>
          <ElTableColumn
            label="结果"
            width="100">
            <template #default="{ row }"><ElTag :type="statusType(row.outcome)">{{ row.outcome || '-' }}</ElTag></template>
          </ElTableColumn>
        </DataTable>
      </ElTabPane>
      <ElTabPane
        v-if="riskVisibilityChecked && riskVisible"
        label="耗尽风险"
        name="exhaustion-risk"
        lazy>
        <CapacityExhaustionRiskPanel
          asset-type="storage_usage"
          :asset-id="usageId" />
      </ElTabPane>
      <ElTabPane
        label="关联事件"
        name="incidents"
        lazy>
        <DataTable
          :data="incidents"
          :loading="loading.incidents"
          :error="errors.incidents">
          <ElTableColumn
            label="事件编号"
            prop="id"
            width="110" />
          <ElTableColumn
            label="类别"
            prop="category"
            min-width="160" />
          <ElTableColumn
            label="严重度"
            width="110">
            <template #default="{ row }"><ElTag :type="statusType(row.severity)">{{ row.severity || '-' }}</ElTag></template>
          </ElTableColumn>
          <ElTableColumn
            label="状态"
            prop="status"
            width="120" />
          <ElTableColumn
            label="RCA 置信度"
            prop="rca_confidence"
            width="130" />
          <ElTableColumn
            label="更新时间"
            prop="updated_at"
            min-width="190" />
        </DataTable>
      </ElTabPane>
    </ElTabs>
    <QuotaAdjustmentDialog
      ref="quotaAdjustmentDialogRef"
      resource-type="storage_usage"
      @submitted="handleQuotaAdjusted" />
  </section>
</template>

<style scoped>
.usage-detail-page {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.usage-detail-page__actions {
  display: flex;
  flex: 0 0 auto;
  justify-content: flex-end;
}

.usage-detail-page__tabs {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.usage-detail-page__tabs :deep(.el-tabs__header) {
  flex: 0 0 auto;
}

.usage-detail-page__tabs :deep(.el-tabs__content) {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
}

.usage-detail-page__tabs :deep(.el-tab-pane) {
  flex: 1 1 auto;
  min-width: 0;
  width: 100%;
}

.usage-detail-page__capacity-tab {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
}

.usage-detail-page__realtime-content {
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
}

</style>
