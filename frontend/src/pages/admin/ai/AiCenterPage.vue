<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  ElButton,
  ElDialog,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTabPane,
  ElTableColumn,
  ElTabs,
  ElTag,
} from 'element-plus';
import aiApi from '@/api/ai-api';
import { useDialog } from '@/composables/dialog';
import TableActionButton from '@/components/basic/TableActionButton.vue';
import DataTable from '@/components/data/DataTable.vue';
import QueryForm from '@/components/form/QueryForm.vue';

const providerOptions = [
  { value: 'openai', label: 'OpenAI', baseUrl: 'https://api.openai.com/v1' },
  { value: 'openrouter', label: 'OpenRouter', baseUrl: 'https://openrouter.ai/api/v1' },
  { value: 'ollama', label: 'Ollama', baseUrl: 'http://localhost:11434' },
  { value: 'claude', label: 'Claude API', baseUrl: 'https://api.anthropic.com' },
  { value: 'claude_code', label: 'Claude Code', baseUrl: 'https://api.anthropic.com' },
  { value: 'deepseek', label: 'DeepSeek', baseUrl: 'https://api.deepseek.com' },
  { value: 'dashscope', label: '通义千问', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { value: 'volcengine', label: '豆包', baseUrl: 'https://ark.cn-beijing.volces.com/api/v3' },
  { value: 'zhipu', label: '智谱 GLM', baseUrl: 'https://open.bigmodel.cn/api/paas/v4' },
  { value: 'moonshot', label: 'Kimi', baseUrl: 'https://api.moonshot.cn/v1' },
  { value: 'minimax', label: 'MiniMax', baseUrl: 'https://api.minimaxi.com/v1' },
  { value: 'qianfan', label: '百度千帆', baseUrl: 'https://qianfan.baidubce.com/v2' },
  { value: 'hunyuan', label: '腾讯混元', baseUrl: 'https://tokenhub.tencentmaas.com/v1' },
];
const defaultProvider = providerOptions[0];

const route = useRoute();
const router = useRouter();
const activeTab = ref(['models', 'audit'].includes(route.query.tab) ? route.query.tab : 'models');
const models = ref([]);
const audits = ref([]);
const total = ref(0);
const loading = ref(false);
const editingId = ref(null);
const defaultModelId = ref(null);
const settingsSubmitting = ref(false);
const auditQuery = reactive({ page: 1, size: 20, status: '' });
const form = reactive({
  name: '',
  description: '',
  provider: 'openai',
  base_url: defaultProvider.baseUrl,
  api_key: '',
  model: '',
  enabled: false,
  enable_chat: true,
  temperature: 0.3,
  max_tokens: 2048,
  system_prompt: '',
});
const modelSubmitting = ref(false);
const discoveringModels = ref(false);
const discoveredModels = ref([]);
const modelDiscoveryStatus = ref('idle');
const formSnapshot = ref(JSON.stringify(form));
const isModelDirty = computed(() => JSON.stringify(form) !== formSnapshot.value);
const availableDefaultModels = computed(() => models.value.filter(
  (model) => model.enabled && model.enable_chat,
));
const {
  visible: dialogVisible,
  open: openModelDialog,
  close: closeModelDialog,
  beforeClose,
  forceClose,
} = useDialog({ isDirty: isModelDirty, isBusy: modelSubmitting });

watch(activeTab, (tab) => {
  router.replace({ query: { ...route.query, tab } });
  if (tab === 'audit') loadAudits();
});

async function loadModels() {
  models.value = await aiApi.listAdminModels();
}

async function loadAiSettings() {
  if (typeof aiApi.getAiSettings !== 'function') return;
  const settings = await aiApi.getAiSettings();
  defaultModelId.value = settings.default_chat_model_id ?? null;
}

async function saveDefaultModel() {
  if (settingsSubmitting.value) return;
  settingsSubmitting.value = true;
  try {
    const settings = await aiApi.updateAiSettings({
      default_chat_model_id: defaultModelId.value,
    });
    defaultModelId.value = settings.default_chat_model_id ?? null;
    models.value = models.value.map((model) => ({
      ...model,
      is_default: model.id === defaultModelId.value,
    }));
    ElMessage.success('默认聊天模型已更新');
  } finally {
    settingsSubmitting.value = false;
  }
}

async function loadAudits() {
  loading.value = true;
  try {
    const result = await aiApi.listAudits({
      ...auditQuery,
      status: auditQuery.status || undefined,
    });
    audits.value = result.content;
    total.value = result.total;
  } finally {
    loading.value = false;
  }
}

function queryAudits() {
  auditQuery.page = 1;
  loadAudits();
}

function resetAuditFilters() {
  auditQuery.status = '';
  queryAudits();
}

function updateAuditPagination(next) {
  auditQuery.page = next.page;
  auditQuery.size = next.pageSize;
  loadAudits();
}

function resetForm() {
  Object.assign(form, {
    name: '', description: '', provider: defaultProvider.value, base_url: defaultProvider.baseUrl, api_key: '', model: '',
    enabled: false, enable_chat: true, temperature: 0.3, max_tokens: 2048, system_prompt: '',
  });
  discoveredModels.value = [];
  modelDiscoveryStatus.value = 'idle';
}

function applyProviderPreset(provider) {
  const preset = providerOptions.find((item) => item.value === provider);
  form.provider = provider;
  if (preset) form.base_url = preset.baseUrl;
  discoveredModels.value = [];
  modelDiscoveryStatus.value = 'idle';
}

function addModel() {
  editingId.value = null;
  resetForm();
  formSnapshot.value = JSON.stringify(form);
  openModelDialog();
}

function editModel(model) {
  editingId.value = model.id;
  Object.assign(form, {
    name: model.name,
    description: model.description || '',
    provider: model.provider,
    base_url: model.base_url || '',
    api_key: '',
    model: model.model,
    enabled: model.enabled,
    enable_chat: model.enable_chat,
    temperature: Number(model.temperature),
    max_tokens: model.max_tokens,
    system_prompt: model.system_prompt || '',
  });
  discoveredModels.value = model.model ? [model.model] : [];
  modelDiscoveryStatus.value = 'idle';
  formSnapshot.value = JSON.stringify(form);
  openModelDialog();
}

async function saveModel() {
  if (modelSubmitting.value) return;
  if (!form.model.trim() && (!editingId.value || form.api_key)) {
    const discovered = await discoverModels();
    if (!discovered) return;
  }
  modelSubmitting.value = true;
  try {
    const payload = { ...form };
    if (editingId.value && !payload.api_key) delete payload.api_key;
    if (editingId.value) await aiApi.updateModel(editingId.value, payload);
    else await aiApi.createModel(payload);
    formSnapshot.value = JSON.stringify(form);
    forceClose();
    ElMessage.success(editingId.value ? '模型配置已更新' : '模型配置已创建');
    await loadModels();
  } finally {
    modelSubmitting.value = false;
  }
}

async function discoverModels({ quiet = false } = {}) {
  if (discoveringModels.value) return false;
  discoveringModels.value = true;
  modelDiscoveryStatus.value = 'loading';
  try {
    const result = await aiApi.discoverModels({
      provider: form.provider,
      base_url: form.base_url.trim(),
      api_key: form.api_key,
    });
    discoveredModels.value = Array.isArray(result.models)
      ? result.models.filter((item) => typeof item === 'string' && item.trim())
      : [];
    const defaultModel = typeof result.default_model === 'string' ? result.default_model.trim() : '';
    if (!form.model.trim() && defaultModel) form.model = defaultModel;
    modelDiscoveryStatus.value = discoveredModels.value.length ? 'ready' : 'failed';
    if (!discoveredModels.value.length) {
      if (!quiet) ElMessage.error('未获取到可用模型，请手工填写模型标识');
      return false;
    }
    if (!quiet) ElMessage.success(`已获取 ${discoveredModels.value.length} 个模型`);
    return true;
  } catch {
    modelDiscoveryStatus.value = 'failed';
    if (!quiet) ElMessage.error('模型列表获取失败，请检查连接或手工填写模型标识');
    return false;
  } finally {
    discoveringModels.value = false;
  }
}

async function testModel(model) {
  const result = await aiApi.testModel(model.id);
  ElMessage.success(`${result.message}：${result.reply || 'OK'}`);
}

function capabilitySourceText(value) {
  return {
    provider: 'Provider 动态能力',
    official_catalog: '官方能力目录',
    unknown: '未知',
  }[value] || '未知';
}

function modelDiscoveryStatusText(value) {
  return {
    idle: '待获取',
    loading: '获取中',
    ready: '已获取',
    failed: '获取失败',
  }[value] || '待获取';
}

function capabilityStatusText(value) {
  return {
    ready: '已获取',
    failed: '获取失败',
    unknown: '未知',
    pending: '获取中',
  }[value] || '未知';
}

function reasoningKindText(value) {
  return {
    effort: '推理强度',
    toggle: '思考开关',
    none: '不可调节',
  }[value] || '未知';
}

function formatCapabilityUpdatedAt(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  const pad = (part) => String(part).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

async function refreshCapabilities(model) {
  const result = await aiApi.refreshModelCapabilities(model.id);
  if (result.status === 'ready') {
    ElMessage.success('模型能力已刷新');
  } else {
    ElMessage.warning('模型能力获取失败，配置已保存；聊天将仅允许自动模式');
  }
  await loadModels();
}

async function deleteModel(model) {
  await aiApi.deleteModel(model.id);
  ElMessage.success('模型配置已删除');
  await loadModels();
}

function confirmDeleteModel(model) {
  ElMessageBox.confirm(`确认删除模型配置「${model.name}」？此操作不可撤销。`, '删除模型配置', {
    type: 'warning',
    confirmButtonText: '删除模型',
    cancelButtonText: '取消',
  }).then(() => deleteModel(model)).catch(() => {});
}

function openAudit(row) {
  router.push(`/admin/ai-center/audits/${row.id}`);
}

function statusType(value) {
  return { succeeded: 'success', failed: 'danger', cancelled: 'warning', running: 'info' }[value] || 'info';
}

onMounted(async () => {
  await Promise.all([loadModels(), loadAiSettings()]);
  if (activeTab.value === 'audit') await loadAudits();
});
</script>

<template>
  <section class="ai-center">
    <ElTabs v-model="activeTab">
      <ElTabPane
        label="模型管理"
        name="models">
        <div class="ai-default-model">
          <div>
            <strong>默认聊天模型</strong>
            <span>新会话将优先使用此模型</span>
          </div>
          <ElSelect
            v-model="defaultModelId"
            class="ai-default-model__select"
            aria-label="默认聊天模型"
            clearable
            placeholder="请选择默认模型">
            <ElOption
              v-for="model in availableDefaultModels"
              :key="model.id"
              :label="model.name"
              :value="model.id" />
          </ElSelect>
          <ElButton
            type="primary"
            :loading="settingsSubmitting"
            @click="saveDefaultModel">
            保存默认模型
          </ElButton>
        </div>
        <DataTable :data="models">
          <ElTableColumn
            prop="name"
            label="名称"
            min-width="160">
            <template #default="{ row }">
              <span>{{ row.name }}</span>
              <ElTag
                v-if="row.is_default"
                class="ai-model-default-tag"
                type="success"
                size="small">
                默认
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn
            prop="provider"
            label="Provider"
            width="120" />
          <ElTableColumn
            prop="model"
            label="模型"
            min-width="160" />
          <ElTableColumn
            label="推理控制"
            min-width="120">
            <template #default="{ row }">
              {{ reasoningKindText(row.reasoning_control?.kind) }}
            </template>
          </ElTableColumn>
          <ElTableColumn
            label="能力来源"
            min-width="140">
            <template #default="{ row }">
              {{ capabilitySourceText(row.capability_source || row.reasoning_control?.source) }}
            </template>
          </ElTableColumn>
          <ElTableColumn
            label="能力状态"
            min-width="120">
            <template #default="{ row }">
              <ElTag :type="(row.capability_status || row.reasoning_control?.status) === 'ready' ? 'success' : 'warning'">
                {{ capabilityStatusText(row.capability_status || row.reasoning_control?.status) }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn
            label="刷新时间"
            min-width="180">
            <template #default="{ row }">
              <time :datetime="row.capability_updated_at">
                {{ formatCapabilityUpdatedAt(row.capability_updated_at) }}
              </time>
            </template>
          </ElTableColumn>
          <ElTableColumn
            label="密钥"
            width="150"><template #default="{ row }">{{ row.api_key_masked || '未配置' }}</template></ElTableColumn>
          <ElTableColumn
            label="状态"
            width="110"><template #default="{ row }"><ElTag :type="row.enabled && row.enable_chat ? 'success' : 'info'">{{ row.enabled && row.enable_chat ? '可对话' : '已停用' }}</ElTag></template></ElTableColumn>
          <ElTableColumn
            label="操作"
            align="right"
            width="132"
            fixed="right">
            <template #header>
              <TableActionButton
                action="create"
                @click="addModel">新增模型</TableActionButton>
            </template>
            <template #default="{ row }">
              <div class="list-row-actions">
                <TableActionButton
                  action="edit"
                  @click="editModel(row)">编辑</TableActionButton>
                <ElDropdown
                  trigger="click"
                  placement="bottom-end">
                  <ElButton
                    class="list-row-actions__more"
                    size="small"
                    plain
                    aria-label="更多操作">
                    ···
                  </ElButton>
                  <template #dropdown>
                    <ElDropdownMenu>
                      <ElDropdownItem @click="testModel(row)">
                        连接测试
                      </ElDropdownItem>
                      <ElDropdownItem @click="refreshCapabilities(row)">
                        刷新能力
                      </ElDropdownItem>
                      <ElDropdownItem
                        class="list-row-actions__danger"
                        @click="confirmDeleteModel(row)">
                        删除
                      </ElDropdownItem>
                    </ElDropdownMenu>
                  </template>
                </ElDropdown>
              </div>
            </template>
          </ElTableColumn>
        </DataTable>
      </ElTabPane>

      <ElTabPane
        label="审计"
        name="audit">
        <QueryForm
          @query="queryAudits"
          @reset="resetAuditFilters">
          <ElFormItem label="状态">
            <ElSelect
              v-model="auditQuery.status"
              clearable
              placeholder="全部状态">
              <ElOption
                label="成功"
                value="succeeded" /><ElOption
                  label="失败"
                  value="failed" />
              <ElOption
                label="已取消"
                value="cancelled" /><ElOption
                  label="执行中"
                  value="running" />
            </ElSelect>
          </ElFormItem>
        </QueryForm>
        <DataTable
          :data="audits"
          :loading="loading"
          :pagination="{
            page: auditQuery.page,
            pageSize: auditQuery.size,
            total,
            pageSizes: [20, 50, 100],
            hideOnSinglePage: true,
            showJumper: true,
          }"
          @update:pagination="updateAuditPagination">
          <ElTableColumn
            prop="id"
            label="ID"
            width="80" />
          <ElTableColumn
            label="会话"
            min-width="160"><template #default="{ row }">{{ row.conversation?.title || '-' }}</template></ElTableColumn>
          <ElTableColumn
            label="用户"
            min-width="120"><template #default="{ row }">{{ row.user?.rd_username || row.user?.username || '-' }}</template></ElTableColumn>
          <ElTableColumn
            label="模型"
            min-width="140"><template #default="{ row }">{{ row.model?.name || row.model?.model || '-' }}</template></ElTableColumn>
          <ElTableColumn
            label="状态"
            width="110"><template #default="{ row }"><ElTag :type="statusType(row.status)">{{ row.status }}</ElTag></template></ElTableColumn>
          <ElTableColumn
            label="工具调用"
            min-width="160"
            show-overflow-tooltip><template #default="{ row }">{{ row.tool_names?.join('、') || '-' }}</template></ElTableColumn>
          <ElTableColumn
            prop="started_at"
            label="开始时间"
            min-width="180" />
          <ElTableColumn
            prop="error_message"
            label="错误摘要"
            min-width="220"
            show-overflow-tooltip />
          <ElTableColumn
            label="操作"
            width="100"
            align="right"
            fixed="right">
            <template #default="{ row }">
              <div class="list-row-actions">
                <TableActionButton
                  action="detail"
                  @click="openAudit(row)">查看</TableActionButton>
              </div>
            </template>
          </ElTableColumn>
        </DataTable>
      </ElTabPane>
    </ElTabs>

    <ElDialog
      v-model="dialogVisible"
      class="write-form-dialog"
      :title="editingId ? '编辑模型' : '新增模型'"
      :before-close="beforeClose">
      <template #header>
        <div class="write-form-dialog__heading">
          <h2>{{ editingId ? '编辑模型' : '新增模型' }}</h2>
        </div>
      </template>
      <ElForm
        class="write-form write-form-grid"
        :model="form"
        label-position="top">
        <div class="write-form-section">模型信息</div>
        <ElFormItem
          label="名称"
          required><ElInput
            v-model="form.name"
            maxlength="100" /></ElFormItem>
        <ElFormItem
          label="Provider"
          required><ElSelect
            v-model="form.provider"
            class="model-provider-select"
            @change="applyProviderPreset"><ElOption
              v-for="provider in providerOptions"
              :key="provider.value"
              :label="provider.label"
              :value="provider.value" /></ElSelect></ElFormItem>
        <ElFormItem label="Base URL"><ElInput
          v-model="form.base_url"
          class="model-base-url"
          placeholder="留空使用 Provider 默认地址" /></ElFormItem>
        <ElFormItem label="API Key"><ElInput
          v-model="form.api_key"
          type="password"
          show-password
          :placeholder="editingId ? '留空表示不修改' : 'Ollama 可留空'" /></ElFormItem>
        <ElFormItem label="模型标识">
          <div class="model-discovery">
            <ElSelect
              v-model="form.model"
              class="model-discovery__select"
              filterable
              allow-create
              clearable
              :loading="discoveringModels"
              placeholder="留空时保存后自动获取">
              <ElOption
                v-for="modelId in discoveredModels"
                :key="modelId"
                :label="modelId"
                :value="modelId" />
            </ElSelect>
            <ElButton
              :loading="discoveringModels"
              @click="discoverModels">
              获取模型
            </ElButton>
            <div
              class="model-discovery__hint"
              aria-live="polite">
              填写时直接作为默认模型；留空时自动获取。模型列表状态：{{ modelDiscoveryStatusText(modelDiscoveryStatus) }}
            </div>
          </div>
        </ElFormItem>
        <ElFormItem label="描述"><ElInput v-model="form.description" /></ElFormItem>
        <div class="write-form-section">生成参数</div>
        <ElFormItem label="Temperature"><ElInputNumber
          v-model="form.temperature"
          :min="0"
          :max="2"
          :step="0.1" /></ElFormItem>
        <ElFormItem label="最大 Token"><ElInputNumber
          v-model="form.max_tokens"
          :min="1"
          :max="128000" /></ElFormItem>
        <ElFormItem
          class="write-form-field--full"
          label="系统提示词"><ElInput
            v-model="form.system_prompt"
            type="textarea"
            :rows="3" /></ElFormItem>
        <div class="write-form-section">可用状态</div>
        <ElFormItem label="启用配置"><ElSwitch v-model="form.enabled" /></ElFormItem>
        <ElFormItem label="允许对话"><ElSwitch v-model="form.enable_chat" /></ElFormItem>
      </ElForm>
      <template #footer><ElButton
        :disabled="modelSubmitting"
        @click="closeModelDialog">取消</ElButton><ElButton
          type="primary"
          :loading="modelSubmitting"
          @click="saveModel">
          {{ modelSubmitting ? (editingId ? '保存中…' : '创建中…') : (editingId ? '保存修改' : '创建模型') }}
        </ElButton></template>
    </ElDialog>
  </section>
</template>

<style scoped>
.ai-default-model {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}
.ai-default-model > div:first-child {
  display: flex;
  flex: 1;
  min-width: 180px;
  flex-direction: column;
  gap: 2px;
}
.ai-default-model span {
  color: var(--text-tertiary);
  font-size: 12px;
}
.model-discovery {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
}
.model-discovery__select {
  min-width: 0;
}
.model-discovery__hint {
  grid-column: 1 / -1;
  color: var(--text-tertiary);
  font-size: 12px;
  line-height: 1.5;
}
.ai-default-model__select {
  width: min(320px, 40vw);
}
.ai-model-default-tag {
  margin-left: 8px;
}
@media (max-width: 720px) {
  .ai-default-model {
    align-items: stretch;
    flex-direction: column;
  }
  .ai-default-model__select {
    width: 100%;
  }
}
</style>
