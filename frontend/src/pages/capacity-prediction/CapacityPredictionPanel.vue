<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { ElAlert, ElButton, ElDatePicker, ElDescriptions, ElDescriptionsItem, ElDialog, ElEmpty, ElForm, ElFormItem, ElInput, ElInputNumber, ElMessage, ElTable, ElTableColumn, ElTag } from 'element-plus';
import capacityPredictionApi from '@/api/capacity-prediction-api.js';
import { getChartColors, loadEcharts } from '@/lib/echarts.js';
import TableActionButton from '@/components/basic/TableActionButton.vue';

const props = defineProps({ assetType: { type: String, required: true }, assetId: { type: Number, required: true }, visible: { type: Boolean, default: false }, canManagePlans: { type: Boolean, default: false } });
const prediction = ref(null);
const plans = ref([]);
const relatedIncidents = ref([]);
const loading = ref(false);
const error = ref('');
const planDialogVisible = ref(false);
const savingPlan = ref(false);
const planForm = reactive({ effectiveAt: null, capacityDelta: 0, reason: '' });
const chartElement = ref(null);
let chart;
const qualityLabel = computed(() => prediction.value?.input_quality?.coverage_ratio == null ? '待评估' : `${Math.round(prediction.value.input_quality.coverage_ratio * 100)}%`);
const qualityStatus = computed(() => prediction.value?.input_quality?.status || 'unknown');
const predictionSource = computed(() => prediction.value?.input_quality?.prediction_source || 'baseline');
const fallbackReason = computed(() => prediction.value?.input_quality?.fallback_reason || null);
const auditSummary = computed(() => {
  if (plans.value.length === 0) return '暂无针对该资源的容量计划审计记录';
  return `该资源已有 ${plans.value.length} 项已审计容量计划，最新生效时间：${plans.value.at(-1)?.effective_at || '-'}`;
});

async function load() {
  if (!props.visible || !props.assetId) return;
  loading.value = true; error.value = '';
  try {
    const [forecastResult, plansResult, incidentsResult] = await Promise.allSettled([
      capacityPredictionApi.fetchPrediction(props.assetType, props.assetId),
      capacityPredictionApi.fetchPlans(props.assetType, props.assetId),
      capacityPredictionApi.fetchRelatedIncidents(props.assetType, props.assetId),
    ]);
    if (forecastResult.status === 'rejected' && forecastResult.reason?.response?.status !== 404) {
      throw forecastResult.reason;
    }
    if (plansResult.status === 'rejected') throw plansResult.reason;
    if (incidentsResult.status === 'rejected') throw incidentsResult.reason;
    prediction.value = forecastResult.status === 'fulfilled' ? forecastResult.value : null;
    plans.value = plansResult.value || [];
    relatedIncidents.value = incidentsResult.value || [];
    await nextTick();
    renderChart();
  } catch {
    prediction.value = null; plans.value = []; relatedIncidents.value = []; error.value = '容量预测暂不可用，请检查数据质量或稍后重试';
  } finally { loading.value = false; }
}
watch(() => [props.assetType, props.assetId, props.visible], load, { immediate: true });
onBeforeUnmount(() => chart?.dispose());

async function renderChart() {
  if (!chartElement.value || !prediction.value?.curve?.length) return;
  const echarts = await loadEcharts();
  chart?.dispose();
  chart = echarts.init(chartElement.value);
  const colors = getChartColors();
  const curve = prediction.value.curve;
  chart.setOption({
    color: [colors[0], colors[2], colors[3]],
    grid: { top: 24, right: 24, bottom: 28, left: 56 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: curve.map((point) => String(point.observed_at).slice(0, 10)) },
    yAxis: { type: 'value', name: '容量' },
    series: [
      { name: 'P10', type: 'line', data: curve.map((point) => point.p10), symbol: 'none' },
      { name: 'P50', type: 'line', data: curve.map((point) => point.p50), symbol: 'none', lineStyle: { width: 3 } },
      { name: 'P90', type: 'line', data: curve.map((point) => point.p90), symbol: 'none' },
    ],
  });
}

function openPlanDialog() {
  planForm.effectiveAt = new Date();
  planForm.capacityDelta = 0;
  planForm.reason = '';
  planDialogVisible.value = true;
}

async function createPlan() {
  if (!planForm.effectiveAt || !planForm.reason.trim() || !planForm.capacityDelta) return;
  savingPlan.value = true;
  try {
    await capacityPredictionApi.createPlan(props.assetType, props.assetId, {
      effective_at: new Date(planForm.effectiveAt).toISOString(),
      capacity_delta: Number(planForm.capacityDelta),
      reason: planForm.reason.trim(),
    });
    ElMessage.success('容量计划已保存');
    planDialogVisible.value = false;
    await load();
  } catch {
    ElMessage.error('保存容量计划失败，请确认项目管理员权限后重试');
  } finally {
    savingPlan.value = false;
  }
}
</script>

<template>
  <section
    v-if="visible"
    v-loading="loading"
    class="capacity-prediction-panel">
    <ElAlert
      v-if="error"
      type="warning"
      :closable="false"
      :title="error" />
    <ElEmpty
      v-else-if="!prediction"
      description="暂无可用容量预测" />
    <template v-else>
      <ElDescriptions
        :column="4"
        border>
        <ElDescriptionsItem label="模型版本"><ElTag>{{ prediction.input_quality?.candidate_version || prediction.algorithm_version }}</ElTag></ElDescriptionsItem>
        <ElDescriptionsItem label="预测来源"><ElTag :type="predictionSource === 'baseline_fallback' ? 'warning' : 'info'">{{ predictionSource === 'baseline_fallback' ? '基线回退' : predictionSource === 'ai_candidate' ? 'AI 候选' : '内置基线' }}</ElTag></ElDescriptionsItem>
        <ElDescriptionsItem label="回测 MAPE">{{ prediction.backtest_mape == null ? '样本不足' : `${prediction.backtest_mape}%` }}</ElDescriptionsItem>
        <ElDescriptionsItem label="数据质量">{{ qualityStatus }} / {{ qualityLabel }}</ElDescriptionsItem>
        <ElDescriptionsItem label="P50 耗尽日期">{{ prediction.exhaustion_dates?.p50 || '30 天内无耗尽风险' }}</ElDescriptionsItem>
        <ElDescriptionsItem label="样本量">{{ prediction.input_quality?.sample_count ?? '-' }} 天</ElDescriptionsItem>
        <ElDescriptionsItem label="最新遥测">{{ prediction.input_quality?.latest_observed_at || '-' }}</ElDescriptionsItem>
        <ElDescriptionsItem label="预测新鲜度">{{ prediction.input_quality?.forecast_fresh_at || prediction.training_end }}</ElDescriptionsItem>
      </ElDescriptions>
      <ElAlert
        v-if="fallbackReason"
        type="warning"
        :closable="false"
        title="AI 候选输出不可用，当前结果已使用基线回退" />
      <div
        ref="chartElement"
        class="capacity-prediction-panel__chart"
        aria-label="容量预测趋势图" />
      <ElTable
        :data="prediction.curve"
        empty-text="预测数据不足">
        <ElTableColumn
          label="日期"
          prop="observed_at"
          min-width="180" />
        <ElTableColumn
          label="P10"
          prop="p10" />
        <ElTableColumn
          label="P50"
          prop="p50" />
        <ElTableColumn
          label="P90"
          prop="p90" />
      </ElTable>
      <div class="capacity-prediction-panel__plans"><span>已批准容量计划：{{ plans.length }} 项</span><TableActionButton
        v-if="canManagePlans"
        action="create"
        @click="openPlanDialog">新增计划</TableActionButton></div>
      <p class="capacity-prediction-panel__audit">审计摘要：{{ auditSummary }}</p>
      <ElTable
        :data="relatedIncidents"
        empty-text="暂无关联事件或 RCA">
        <ElTableColumn
          label="关联事件"
          prop="id" />
        <ElTableColumn
          label="严重度"
          prop="severity" />
        <ElTableColumn
          label="状态"
          prop="status" />
        <ElTableColumn label="RCA 置信度">
          <template #default="{ row }">{{ row.rca_confidence || '待生成' }}</template>
        </ElTableColumn>
      </ElTable>
      <p class="capacity-prediction-panel__incident-boundary">关联事件：容量风险、异常与 RCA 请在事件中心查看；原始告警和厂商系统事件仍保留在原有入口。</p>
    </template>
    <ElDialog
      v-model="planDialogVisible"
      title="新增容量计划"
      width="520px">
      <ElForm label-position="top">
        <ElFormItem label="生效时间"><ElDatePicker
          v-model="planForm.effectiveAt"
          type="datetime"
          class="!w-full" /></ElFormItem>
        <ElFormItem label="容量变化"><ElInputNumber
          v-model="planForm.capacityDelta"
          :min="-1000000000"
          :max="1000000000"
          class="!w-full" /></ElFormItem>
        <ElFormItem label="批准说明"><ElInput
          v-model="planForm.reason"
          type="textarea"
          :maxlength="500"
          show-word-limit /></ElFormItem>
      </ElForm>
      <template #footer><ElButton @click="planDialogVisible = false">取消</ElButton><ElButton
        type="primary"
        :loading="savingPlan"
        @click="createPlan">保存计划</ElButton></template>
    </ElDialog>
  </section>
</template>

<style scoped>
.capacity-prediction-panel { display: grid; gap: var(--spacing-md); }
.capacity-prediction-panel__chart { min-height: 280px; }
.capacity-prediction-panel__plans { display: flex; align-items: center; justify-content: space-between; margin: 0; color: var(--text-secondary); font-size: var(--font-size-sm); }
.capacity-prediction-panel__audit { margin: 0; color: var(--text-secondary); font-size: var(--font-size-sm); }
.capacity-prediction-panel__incident-boundary { margin: 0; color: var(--text-secondary); font-size: var(--font-size-sm); }
</style>
