<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import {
  ElDescriptions,
  ElDescriptionsItem,
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
import alertApi from '@/api/alert-api.js';
import { formatQuotaLimit } from '@/utils/quota';

const route = useRoute();
const breadcrumbs = useBreadcrumbs();
const usageId = computed(() => Number(route.params?.id));
const activeTab = ref('capacity');
const usage = ref(null);
const usageLoading = ref(false);
const usageError = ref('');
const predictionVisible = ref(false);
const predictionVisibilityChecked = ref(false);
const quotaHistory = ref([]);
const prediction = ref(null);
const incidents = ref([]);
const alerts = ref([]);
const loaded = reactive({ quotaHistory: false, prediction: false, incidents: false, alerts: false });
const loading = reactive({ quotaHistory: false, prediction: false, incidents: false, alerts: false });
const errors = reactive({ quotaHistory: '', prediction: '', incidents: '', alerts: '' });
const canViewQuotaHistory = computed(() => usage.value?.capabilities?.adjust_quota === true);

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

function predictionSource(value) {
  return {
    ai_candidate: 'AI 候选',
    baseline_fallback: '基线回退',
    baseline: '内置基线',
  }[value] || '内置基线';
}

function latestP50(curve) {
  const values = Array.isArray(curve) ? curve : [];
  return values.length ? values.at(-1)?.p50 ?? '-' : '-';
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

async function loadPredictionVisibility() {
  try {
    const result = await capacityPredictionApi.visibility();
    predictionVisible.value = result.visible === true;
  } catch {
    predictionVisible.value = false;
  } finally {
    predictionVisibilityChecked.value = true;
    if (predictionVisible.value) await loadActiveTab();
  }
}

async function loadPrediction() {
  if (!predictionVisible.value || loaded.prediction || loading.prediction) return;
  loading.prediction = true;
  errors.prediction = '';
  try {
    prediction.value = await capacityPredictionApi.fetchPrediction('storage_usage', usageId.value, {
      errorHandlerDisabled: true,
    });
    loaded.prediction = true;
  } catch (error) {
    prediction.value = null;
    if (error?.response?.status === 404) {
      loaded.prediction = true;
    } else if (error?.response?.status === 403) {
      predictionVisible.value = false;
      activeTab.value = 'capacity';
    } else {
      errors.prediction = '加载容量预测最终结果失败，请稍后重试';
    }
  } finally {
    loading.prediction = false;
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

async function loadAlerts() {
  if (loaded.alerts || loading.alerts) return;
  loading.alerts = true;
  errors.alerts = '';
  try {
    const result = await alertApi.fetch({
      related_type: 'StorageUsage',
      related_id: usageId.value,
      page: 1,
      size: 20,
    });
    alerts.value = result.content || [];
    loaded.alerts = true;
  } catch {
    alerts.value = [];
    errors.alerts = '加载关联告警失败，请稍后重试';
  } finally {
    loading.alerts = false;
  }
}

async function loadActiveTab() {
  if (!Number.isInteger(usageId.value) || usageId.value < 1) return;
  if (activeTab.value === 'quota-history') return loadQuotaHistory();
  if (activeTab.value === 'prediction') return loadPrediction();
  if (activeTab.value === 'incidents') return loadIncidents();
  if (activeTab.value === 'alerts') return loadAlerts();
}

watch(activeTab, loadActiveTab);
onMounted(() => {
  breadcrumbs.setDetailBreadcrumb(route.name, []);
  loadUsage();
  loadPredictionVisibility();
});
</script>

<template>
  <section class="usage-detail-page">
    <ElTabs v-model="activeTab">
      <ElTabPane
        label="容量趋势"
        name="capacity">
        <RealTimePage
          :attribute-id="usageId"
          api-type="storage-usage"
          label="用户目录"
          :show-header="false">
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
        v-if="predictionVisibilityChecked && predictionVisible"
        label="容量预测最终结果"
        name="prediction"
        lazy>
        <div
          v-if="loading.prediction"
          class="prediction-loading"
          role="status"
          aria-live="polite">
          正在加载容量预测最终结果
        </div>
        <ElEmpty
          v-else-if="loaded.prediction && !prediction && !errors.prediction"
          description="暂无容量预测最终结果" />
        <DataTable
          v-else-if="errors.prediction"
          :data="[]"
          :error="errors.prediction" />
        <ElDescriptions
          v-else-if="prediction"
          :column="4"
          border>
          <ElDescriptionsItem label="模型版本">{{ prediction.input_quality?.candidate_version || prediction.algorithm_version || '-' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="预测来源">{{ predictionSource(prediction.input_quality?.prediction_source) }}</ElDescriptionsItem>
          <ElDescriptionsItem label="数据质量">{{ prediction.input_quality?.status || '-' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="覆盖率">{{ prediction.input_quality?.coverage_ratio == null ? '-' : `${Math.round(prediction.input_quality.coverage_ratio * 100)}%` }}</ElDescriptionsItem>
          <ElDescriptionsItem label="P50 耗尽日期">{{ prediction.exhaustion_dates?.p50 || '30 天内无耗尽风险' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="最终 P50">{{ latestP50(prediction.curve) }}</ElDescriptionsItem>
          <ElDescriptionsItem label="最新遥测">{{ prediction.input_quality?.latest_observed_at || '-' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="预测生成时间">{{ prediction.input_quality?.forecast_fresh_at || prediction.created_at || '-' }}</ElDescriptionsItem>
        </ElDescriptions>
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
      <ElTabPane
        label="告警"
        name="alerts"
        lazy>
        <DataTable
          :data="alerts"
          :loading="loading.alerts"
          :error="errors.alerts">
          <ElTableColumn
            label="级别"
            width="100">
            <template #default="{ row }"><ElTag :type="statusType(row.alert_level)">{{ row.alert_level || '-' }}</ElTag></template>
          </ElTableColumn>
          <ElTableColumn
            label="事件类型"
            prop="event_type"
            width="120" />
          <ElTableColumn
            label="内容"
            prop="description"
            min-width="280" />
          <ElTableColumn
            label="触发值"
            prop="avg_use_ratio"
            width="100" />
          <ElTableColumn
            label="时间"
            prop="updated_at"
            min-width="190" />
        </DataTable>
      </ElTabPane>
    </ElTabs>
  </section>
</template>

<style scoped>
.usage-detail-page { height: 100%; min-height: 0; }
.usage-detail-page :deep(.el-tabs) { height: 100%; }
.usage-detail-page :deep(.el-tabs__content),
.usage-detail-page :deep(.el-tab-pane) { height: calc(100% - 28px); min-height: 0; }
.prediction-loading { min-height: 160px; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); }
</style>
