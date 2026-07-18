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
  ElInputNumber,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';
import capacityPredictionApi from '@/api/capacity-prediction-api.js';

const visible = ref(false);
const loading = ref(false);
const error = ref('');
const candidates = ref([]);
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

function openCreateDialog() {
  candidateForm.version = '';
  candidateForm.aiModelId = null;
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
    error.value = '创建候选模型失败；仅可使用已启用的私有模型';
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
    <header class="forecast-governance-page__header">
      <div>
        <h2>容量预测治理</h2>
        <p>后台预测和评估持续运行；发布开关仅控制拥有项目权限的成员能否查看资源级预测。</p>
      </div>
      <ElButton
        type="primary"
        @click="openCreateDialog">新增候选模型</ElButton>
    </header>

    <ElAlert
      v-if="error"
      :title="error"
      type="error"
      :closable="false" />

    <section class="forecast-governance-page__setting">
      <div>
        <strong>全局用户可见性</strong>
        <p>关闭后普通用户的页签和读取接口均不可用；超级管理员仍可治理和查看。</p>
      </div>
      <ElSwitch
        :model-value="visible"
        :loading="loading"
        active-text="向项目成员发布"
        inactive-text="仅超级管理员可见"
        @change="update" />
    </section>

    <section class="forecast-governance-page__section">
      <h3>模型状态</h3>
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
            <ElButton
              v-if="!row.enabled"
              size="small"
              :disabled="!row.activation_ready"
              :loading="activatingId === row.id"
              @click="activateCandidate(row)">
              启用
            </ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </section>

    <section class="forecast-governance-page__section">
      <h3>跨资源滚动回测评估</h3>
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
          label="基线 MAPE"
          prop="baseline_mape"
          width="120" />
        <ElTableColumn
          label="候选 MAPE"
          prop="candidate_mape"
          width="120" />
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
        <ElFormItem label="已启用私有模型 ID">
          <ElInputNumber
            v-model="candidateForm.aiModelId"
            :min="1"
            :precision="0"
            class="!w-full" />
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
.forecast-governance-page { display: grid; gap: var(--spacing-lg); }
.forecast-governance-page__header,
.forecast-governance-page__setting { display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md); }
.forecast-governance-page__header h2,
.forecast-governance-page__section h3 { margin: 0; }
.forecast-governance-page__header p,
.forecast-governance-page__setting p { margin: var(--spacing-xs) 0 0; color: var(--text-secondary); }
.forecast-governance-page__setting,
.forecast-governance-page__section { padding: var(--spacing-md); border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-primary); }
.forecast-governance-page__section { display: grid; gap: var(--spacing-md); }
</style>
