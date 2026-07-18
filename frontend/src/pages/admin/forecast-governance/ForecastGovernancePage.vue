<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
  ElAlert,
  ElButton,
  ElDialog,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTag,
  ElTooltip,
} from 'element-plus';
import capacityPredictionApi from '@/api/capacity-prediction-api.js';
import aiApi from '@/api/ai-api.js';
import TableActionButton from '@/components/basic/TableActionButton.vue';

const visible = ref(false);
const loading = ref(false);
const error = ref('');
const candidates = ref([]);
const configuredModels = ref([]);
const activatingId = ref(null);
const createDialogVisible = ref(false);
const creating = ref(false);
const candidateForm = reactive({ version: '', aiModelId: null });

const evaluationRows = computed(() => candidates.value.flatMap((candidate) => (
  (candidate.evaluations || []).map((evaluation) => ({
    ...evaluation,
    version: candidate.version,
    candidate_id: candidate.id,
  }))
)));

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const [settings, rows] = await Promise.all([
      capacityPredictionApi.settings(),
      capacityPredictionApi.fetchCandidates(),
    ]);
    visible.value = settings.visible === true;
    candidates.value = Array.isArray(rows) ? rows : [];
  } catch {
    error.value = '加载预测治理设置失败';
  } finally {
    loading.value = false;
  }
}

async function update(value) {
  loading.value = true;
  error.value = '';
  try {
    visible.value = (await capacityPredictionApi.updateSettings({ user_visible: value })).visible === true;
  } catch {
    error.value = '保存预测可见性失败';
  } finally {
    loading.value = false;
  }
}

async function openCreateDialog() {
  candidateForm.version = '';
  candidateForm.aiModelId = null;
  error.value = '';
  try {
    const models = await aiApi.listAdminModels();
    configuredModels.value = Array.isArray(models) ? models : [];
  } catch {
    configuredModels.value = [];
    error.value = '加载 AI 中心模型失败';
  }
  createDialogVisible.value = true;
}

async function createCandidate() {
  if (!candidateForm.version.trim() || !candidateForm.aiModelId) return;
  creating.value = true;
  error.value = '';
  try {
    await capacityPredictionApi.createCandidate({
      version: candidateForm.version.trim(),
      ai_model_id: Number(candidateForm.aiModelId),
    });
    createDialogVisible.value = false;
    await load();
  } catch {
    error.value = '创建候选模型失败';
  } finally {
    creating.value = false;
  }
}

async function activateCandidate(candidate) {
  activatingId.value = candidate.id;
  error.value = '';
  try {
    await capacityPredictionApi.activateCandidate(candidate.id);
    await load();
  } catch {
    error.value = '候选模型尚未满足三窗口准确率与风险覆盖门槛';
  } finally {
    activatingId.value = null;
  }
}

onMounted(load);
</script>

<template>
  <section
    v-loading="loading"
    class="forecast-governance-page">
    <ElAlert
      v-if="error"
      :title="error"
      type="error"
      :closable="false" />

    <section class="forecast-governance-page__setting">
      <strong>全局用户可见性</strong>
      <ElSwitch
        :model-value="visible"
        :loading="loading"
        active-text="向项目成员发布"
        inactive-text="仅超级管理员可见"
        @change="update" />
      <ElButton
        type="primary"
        @click="openCreateDialog">新增候选模型</ElButton>
    </section>

    <section class="forecast-governance-page__section">
      <h3 class="forecast-governance-page__section-heading">模型状态</h3>
      <ElTable
        :data="candidates"
        empty-text="暂无候选预测模型">
        <ElTableColumn
          label="版本"
          prop="version"
          min-width="160" />
        <ElTableColumn
          label="AI 模型 ID"
          prop="ai_model_id"
          width="120" />
        <ElTableColumn
          label="评估窗口"
          width="120">
          <template #default="{ row }">{{ row.evaluations?.length || 0 }} / 3</template>
        </ElTableColumn>
        <ElTableColumn
          label="AI 回退"
          width="140">
          <template #default="{ row }">
            <ElTag :type="row.fallback_count > 0 ? 'warning' : 'success'">
              {{ row.fallback_count || 0 }} / {{ row.forecast_count || 0 }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn
          label="状态"
          width="150">
          <template #default="{ row }">
            <ElTag :type="row.enabled ? 'success' : row.activation_ready ? 'warning' : 'info'">
              {{ row.enabled ? '当前默认' : row.activation_ready ? '可启用' : '评估中' }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn
          label="操作"
          width="120"
          align="right">
          <template #default="{ row }">
            <TableActionButton
              v-if="!row.enabled"
              action="activate"
              :disabled="!row.activation_ready"
              :loading="activatingId === row.id"
              @click="activateCandidate(row)">
              启用
            </TableActionButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </section>

    <section class="forecast-governance-page__section">
      <h3 class="forecast-governance-page__section-heading">跨资源滚动回测评估</h3>
      <ElEmpty
        v-if="evaluationRows.length === 0"
        description="暂无完成的 30 天评估窗口"
        :image-size="72" />
      <ElTable
        v-else
        :data="evaluationRows">
        <ElTableColumn
          label="版本"
          prop="version"
          min-width="160" />
        <ElTableColumn
          label="评估窗口"
          min-width="260">
          <template #default="{ row }">{{ row.window_start }} 至 {{ row.window_end }}</template>
        </ElTableColumn>
        <ElTableColumn
          prop="baseline_mape"
          width="120">
          <template #header>
            <span class="forecast-governance-page__metric-header">
              基线 MAPE
              <ElTooltip content="基线 MAPE：当前基线预测与实际容量的平均绝对百分比误差，数值越低越准确。">
                <span
                  class="forecast-governance-page__metric-help i-ri-question-line"
                  tabindex="0"
                  aria-label="基线 MAPE 说明" />
              </ElTooltip>
            </span>
          </template>
        </ElTableColumn>
        <ElTableColumn
          prop="candidate_mape"
          width="120">
          <template #header>
            <span class="forecast-governance-page__metric-header">
              候选 MAPE
              <ElTooltip content="候选 MAPE：候选 AI 模型预测与实际容量的平均绝对百分比误差，数值越低越准确。">
                <span
                  class="forecast-governance-page__metric-help i-ri-question-line"
                  tabindex="0"
                  aria-label="候选 MAPE 说明" />
              </ElTooltip>
            </span>
          </template>
        </ElTableColumn>
        <ElTableColumn
          label="耗尽风险覆盖"
          width="130">
          <template #default="{ row }"><ElTag :type="row.risk_coverage_ok ? 'success' : 'danger'">{{ row.risk_coverage_ok ? '不变差' : '不满足' }}</ElTag></template>
        </ElTableColumn>
      </ElTable>
    </section>

    <ElDialog
      v-model="createDialogVisible"
      title="新增容量预测候选模型"
      width="520px">
      <ElForm label-position="top">
        <ElFormItem label="模型版本">
          <ElInput
            v-model="candidateForm.version"
            maxlength="64"
            placeholder="例如 capacity-ai-v2" />
        </ElFormItem>
        <ElFormItem label="AI 中心模型">
          <ElSelect
            v-model="candidateForm.aiModelId"
            class="!w-full"
            placeholder="请选择已配置模型">
            <ElOption
              v-for="model in configuredModels"
              :key="model.id"
              :label="`${model.name}（${model.model}）`"
              :value="model.id" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="createDialogVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="creating"
          @click="createCandidate">创建候选</ElButton>
      </template>
    </ElDialog>
  </section>
</template>

<style scoped>
.forecast-governance-page { display: grid; align-content: start; gap: var(--spacing-lg); }
.forecast-governance-page__setting { display: flex; align-items: center; gap: var(--spacing-md); height: 60px; }
.forecast-governance-page__setting strong { margin-right: auto; }
.forecast-governance-page__section-heading { display: flex; align-items: center; justify-content: flex-start; height: 40px; text-align: left; }
.forecast-governance-page__setting,
.forecast-governance-page__section { padding: var(--spacing-md); border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-primary); }
.forecast-governance-page__section { display: grid; align-content: start; gap: var(--spacing-md); }
.forecast-governance-page__metric-header { display: inline-flex; align-items: center; gap: var(--spacing-xs); }
.forecast-governance-page__metric-help { color: var(--text-tertiary); cursor: help; outline-offset: 2px; }
</style>
