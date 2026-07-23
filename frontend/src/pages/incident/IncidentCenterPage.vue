<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInputNumber,
  ElMessage,
  ElOption,
  ElSelect,
  ElTableColumn,
  ElTag,
} from 'element-plus';
import DataTable from '@/components/data/DataTable.vue';
import QueryForm from '@/components/form/QueryForm.vue';
import incidentApi from '@/api/incident-api.js';
import IncidentDetailDrawer from './components/IncidentDetailDrawer.vue';
import TableActionButton from '@/components/basic/TableActionButton.vue';

const queryParams = reactive({ page: 1, size: 20, status: '', category: '' });
const incidents = ref([]);
const total = ref(0);
const loading = ref(false);
const error = ref('');
const selectedIncident = ref(null);
const detailVisible = ref(false);
const editingIncident = ref(null);
const editVisible = ref(false);
const savingEdit = ref(false);
const editForm = reactive({ severity: 'warning', status: 'open' });
const aiSettingsVisible = ref(false);
const aiSettingsLoading = ref(false);
const aiSettingsSaving = ref(false);
const aiSettingsError = ref('');
const aiSettings = reactive({
  enabled: false,
  model_ids: [],
  available_models: [],
  iops_absolute_floor: 10,
  iops_baseline_ratio: 0.05,
});

function formatLocalDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  const pad = (part) => String(part).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function sortLatestEvidence(items) {
  return [...items].sort((left, right) => {
    const leftAt = Date.parse(left.last_evidence_at);
    const rightAt = Date.parse(right.last_evidence_at);
    if (Number.isNaN(leftAt)) return Number.isNaN(rightAt) ? Number(right.id || 0) - Number(left.id || 0) : 1;
    if (Number.isNaN(rightAt)) return -1;
    return rightAt - leftAt || Number(right.id || 0) - Number(left.id || 0);
  });
}

const statusLabels = {
  open: '未处理',
  acknowledged: '已确认',
  investigating: '调查中',
  mitigated: '已缓解',
  resolved: '已解决',
};

const categoryLabels = {
  capacity_pressure: '容量压力',
  device_fault: '设备健康风险',
  performance_contention: '性能争用',
  telemetry_blindspot: '监控盲区',
};
const aiUrgencyLabels = { low: '低', medium: '中', high: '高', critical: '紧急' };

const selectedAiModels = computed(() => aiSettings.model_ids
  .map((id) => aiSettings.available_models.find((model) => model.id === id))
  .filter(Boolean));

const editableStatusOptions = computed(() => {
  const currentStatus = editingIncident.value?.status;
  const nextStatus = {
    open: 'acknowledged',
    acknowledged: 'investigating',
    investigating: 'mitigated',
    mitigated: 'resolved',
  }[currentStatus];
  return Object.entries(statusLabels).filter(([value]) => value === currentStatus || value === nextStatus);
});

async function query() {
  loading.value = true;
  error.value = '';
  try {
    const result = await incidentApi.fetchIncidents({
      page: queryParams.page,
      size: queryParams.size,
      ...(queryParams.status ? { status: queryParams.status } : {}),
      ...(queryParams.category ? { category: queryParams.category } : {}),
    });
    incidents.value = sortLatestEvidence(result.content || []);
    total.value = Number(result.total) || 0;
  } catch {
    incidents.value = [];
    total.value = 0;
    error.value = '加载事件失败，请稍后重试';
  } finally {
    loading.value = false;
  }
}

function reset() {
  queryParams.page = 1;
  queryParams.status = '';
  queryParams.category = '';
  query();
}

function updatePagination(next) {
  queryParams.page = next.page;
  queryParams.size = next.pageSize;
  query();
}

function openDetail(incident) {
  selectedIncident.value = incident;
  detailVisible.value = true;
}

function openEdit(incident) {
  editingIncident.value = incident;
  editForm.severity = incident.severity;
  editForm.status = incident.status;
  error.value = '';
  editVisible.value = true;
}

async function saveEdit() {
  const incident = editingIncident.value;
  if (!incident?.id) return;
  const payload = {};
  if (editForm.severity !== incident.severity) payload.severity = editForm.severity;
  if (editForm.status !== incident.status) payload.status = editForm.status;
  if (Object.keys(payload).length === 0) {
    editVisible.value = false;
    return;
  }
  savingEdit.value = true;
  error.value = '';
  try {
    await incidentApi.updateIncident(incident.id, payload);
    editVisible.value = false;
    await query();
  } catch {
    error.value = '更新事件失败，请稍后重试';
  } finally {
    savingEdit.value = false;
  }
}

async function openAiSettings() {
  aiSettingsVisible.value = true;
  aiSettingsLoading.value = true;
  aiSettingsError.value = '';
  try {
    const settings = await incidentApi.fetchAiSettings();
    aiSettings.enabled = settings.enabled;
    aiSettings.model_ids = [...(settings.model_ids || [])];
    aiSettings.available_models = settings.available_models || [];
    aiSettings.iops_absolute_floor = Number(settings.iops_absolute_floor ?? 10);
    aiSettings.iops_baseline_ratio = Number(settings.iops_baseline_ratio ?? 0.05);
  } catch {
    aiSettingsError.value = '加载 AI 处置设置失败，请确认超级管理员权限后重试';
  } finally {
    aiSettingsLoading.value = false;
  }
}

function moveAiModel(index, offset) {
  const target = index + offset;
  if (target < 0 || target >= aiSettings.model_ids.length) return;
  const next = [...aiSettings.model_ids];
  [next[index], next[target]] = [next[target], next[index]];
  aiSettings.model_ids = next;
}

async function saveAiSettings() {
  if (aiSettings.enabled && aiSettings.model_ids.length === 0) {
    aiSettingsError.value = '启用 AI 处置前，请至少选择一个已启用的模型';
    return;
  }
  aiSettingsSaving.value = true;
  aiSettingsError.value = '';
  try {
    const saved = await incidentApi.updateAiSettings({
      enabled: aiSettings.enabled,
      model_ids: aiSettings.model_ids,
      iops_absolute_floor: aiSettings.iops_absolute_floor,
      iops_baseline_ratio: aiSettings.iops_baseline_ratio,
    });
    aiSettings.enabled = saved.enabled;
    aiSettings.model_ids = [...saved.model_ids];
    aiSettings.iops_absolute_floor = Number(saved.iops_absolute_floor);
    aiSettings.iops_baseline_ratio = Number(saved.iops_baseline_ratio);
    aiSettingsVisible.value = false;
    ElMessage.success('AI 处置设置已保存');
  } catch {
    aiSettingsError.value = '保存 AI 处置设置失败，请检查模型和参数后重试';
  } finally {
    aiSettingsSaving.value = false;
  }
}

onMounted(query);
</script>

<template>
  <section class="incident-center-page">
    <QueryForm
      @query="{ queryParams.page = 1; query(); }"
      @reset="reset">
      <ElFormItem label="状态">
        <ElSelect
          v-model="queryParams.status"
          clearable
          placeholder="全部状态">
          <ElOption
            v-for="(label, value) in statusLabels"
            :key="value"
            :label="label"
            :value="value" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem label="类别">
        <ElSelect
          v-model="queryParams.category"
          clearable
          placeholder="全部类别">
          <ElOption
            v-for="(label, value) in categoryLabels"
            :key="value"
            :label="label"
            :value="value" />
        </ElSelect>
      </ElFormItem>
    </QueryForm>
    <DataTable
      class="incident-center-page__table"
      :data="incidents"
      :loading="loading"
      :error="error"
      :pagination="{ page: queryParams.page, pageSize: queryParams.size, total, pageSizes: [20, 50, 100], hideOnSinglePage: true, showJumper: true }"
      @update:pagination="updatePagination">
      <ElTableColumn
        label="受影响对象"
        prop="display_name"
        min-width="180" />
      <ElTableColumn
        label="事件类型"
        min-width="120">
        <template #default="{ row }">{{ categoryLabels[row.category] || row.category }}</template>
      </ElTableColumn>
      <ElTableColumn
        label="严重度"
        prop="severity"
        width="110">
        <template #default="{ row }"><ElTag :type="row.severity === 'critical' ? 'danger' : 'warning'">{{ row.severity }}</ElTag></template>
      </ElTableColumn>
      <ElTableColumn
        label="AI 紧急度"
        width="120">
        <template #default="{ row }">
          <ElTag
            v-if="row.ai_urgency"
            :type="row.ai_urgency === 'critical' ? 'danger' : row.ai_urgency === 'high' ? 'warning' : 'info'">{{ aiUrgencyLabels[row.ai_urgency] || row.ai_urgency }}</ElTag>
          <span v-else>-</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="状态"
        width="120">
        <template #default="{ row }">{{ statusLabels[row.status] || row.status }}</template>
      </ElTableColumn>
      <ElTableColumn
        label="最近证据"
        min-width="190">
        <template #default="{ row }">
          <time :datetime="row.last_evidence_at">{{ formatLocalDateTime(row.last_evidence_at) }}</time>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="操作"
        align="right"
        width="150"
        fixed="right">
        <template #header>
          <TableActionButton
            action="edit"
            @click="openAiSettings">AI 处置设置</TableActionButton>
        </template>
        <template #default="{ row }">
          <div class="list-row-actions">
            <TableActionButton
              action="detail"
              @click="openDetail(row)">详情</TableActionButton>
            <TableActionButton
              action="edit"
              @click="openEdit(row)">编辑</TableActionButton>
          </div>
        </template>
      </ElTableColumn>
    </DataTable>
    <IncidentDetailDrawer
      v-model="detailVisible"
      :incident="selectedIncident"
      @updated="query" />
    <ElDialog
      v-model="editVisible"
      title="编辑事件"
      width="420px"
      :close-on-click-modal="false">
      <ElForm label-position="top">
        <ElFormItem label="严重度">
          <ElSelect v-model="editForm.severity">
            <ElOption
              label="warning"
              value="warning" />
            <ElOption
              label="critical"
              value="critical" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="状态">
          <ElSelect v-model="editForm.status">
            <ElOption
              v-for="([value, label]) in editableStatusOptions"
              :key="value"
              :label="label"
              :value="value" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="editVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="savingEdit"
          @click="saveEdit">保存</ElButton>
      </template>
    </ElDialog>
    <ElDialog
      v-model="aiSettingsVisible"
      title="AI 处置设置"
      width="min(560px, calc(100% - 32px))"
      :close-on-click-modal="false">
      <ElForm
        v-loading="aiSettingsLoading"
        label-position="top">
        <p
          v-if="aiSettingsError"
          class="incident-center-page__error">{{ aiSettingsError }}</p>
        <ElFormItem label="启用 AI 处置">
          <ElSelect v-model="aiSettings.enabled">
            <ElOption
              label="启用"
              :value="true" />
            <ElOption
              label="关闭"
              :value="false" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="候选模型（按优先级排序）">
          <ElSelect
            v-model="aiSettings.model_ids"
            multiple
            collapse-tags
            placeholder="选择全局已启用模型">
            <ElOption
              v-for="model in aiSettings.available_models"
              :key="model.id"
              :label="model.name"
              :value="model.id" />
          </ElSelect>
          <ol
            v-if="selectedAiModels.length"
            class="incident-center-page__model-priority">
            <li
              v-for="(model, index) in selectedAiModels"
              :key="model.id">
              <span>{{ index + 1 }}. {{ model.name }}</span>
              <span class="list-row-actions">
                <TableActionButton
                  action="detail"
                  :disabled="index === 0"
                  @click="moveAiModel(index, -1)">上移</TableActionButton>
                <TableActionButton
                  action="detail"
                  :disabled="index === selectedAiModels.length - 1"
                  @click="moveAiModel(index, 1)">下移</TableActionButton>
              </span>
            </li>
          </ol>
        </ElFormItem>
        <ElFormItem label="IOPS 绝对下限">
          <ElInputNumber
            v-model="aiSettings.iops_absolute_floor"
            :min="0"
            :precision="2"
            :step="1" />
        </ElFormItem>
        <ElFormItem label="IOPS 基线比例">
          <ElInputNumber
            v-model="aiSettings.iops_baseline_ratio"
            :min="0"
            :max="1"
            :precision="3"
            :step="0.01" />
        </ElFormItem>
        <p class="incident-center-page__hint">低于 max(绝对下限，历史基线 × 比例) 的连续短时 IOPS 波动，不创建性能异常事件。</p>
      </ElForm>
      <template #footer>
        <ElButton @click="aiSettingsVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="aiSettingsSaving"
          :disabled="aiSettingsLoading"
          @click="saveAiSettings">保存</ElButton>
      </template>
    </ElDialog>
  </section>
</template>

<style scoped>
.incident-center-page { display: flex; flex-direction: column; gap: var(--spacing-md); }
.incident-center-page__actions { display: flex; justify-content: flex-end; }
.incident-center-page__table { min-height: 420px; }
.incident-center-page__error { margin: 0 0 var(--spacing-sm); color: var(--danger-color); }
.incident-center-page__hint { margin: 0; color: var(--text-secondary); font-size: var(--font-size-sm); }
.incident-center-page__model-priority { display: grid; gap: 6px; width: 100%; margin: 8px 0 0; padding-left: 20px; }
.incident-center-page__model-priority li { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
</style>
