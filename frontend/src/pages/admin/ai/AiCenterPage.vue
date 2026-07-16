<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElOption,
  ElPagination,
  ElPopconfirm,
  ElSelect,
  ElSwitch,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
} from 'element-plus';
import aiApi from '@/api/ai-api';
import { useDialog } from '@/composables/dialog';

const route = useRoute();
const router = useRouter();
const activeTab = ref(['models', 'audit'].includes(route.query.tab) ? route.query.tab : 'models');
const models = ref([]);
const audits = ref([]);
const total = ref(0);
const loading = ref(false);
const editingId = ref(null);
const auditQuery = reactive({ page: 1, size: 20, status: '' });
const form = reactive({
  name: '',
  description: '',
  provider: 'openai',
  base_url: '',
  api_key: '',
  model: '',
  enabled: false,
  enable_chat: true,
  temperature: 0.3,
  max_tokens: 2048,
  system_prompt: '',
});
const modelSubmitting = ref(false);
const formSnapshot = ref(JSON.stringify(form));
const isModelDirty = computed(() => JSON.stringify(form) !== formSnapshot.value);
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

function resetForm() {
  Object.assign(form, {
    name: '', description: '', provider: 'openai', base_url: '', api_key: '', model: '',
    enabled: false, enable_chat: true, temperature: 0.3, max_tokens: 2048, system_prompt: '',
  });
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
  formSnapshot.value = JSON.stringify(form);
  openModelDialog();
}

async function saveModel() {
  if (modelSubmitting.value) return;
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

async function testModel(model) {
  const result = await aiApi.testModel(model.id);
  ElMessage.success(`${result.message}：${result.reply || 'OK'}`);
}

async function deleteModel(model) {
  await aiApi.deleteModel(model.id);
  ElMessage.success('模型配置已删除');
  await loadModels();
}

function openAudit(row) {
  router.push(`/admin/ai-center/audits/${row.id}`);
}

function statusType(value) {
  return { succeeded: 'success', failed: 'danger', cancelled: 'warning', running: 'info' }[value] || 'info';
}

onMounted(async () => {
  await loadModels();
  if (activeTab.value === 'audit') await loadAudits();
});
</script>

<template>
  <section class="ai-center">
    <header>
      <div>
        <h2>AI 中心</h2>
        <p>统一管理模型连接和对话审计，仅超级管理员可访问。</p>
      </div>
    </header>

    <ElTabs v-model="activeTab">
      <ElTabPane
        label="模型管理"
        name="models">
        <div class="toolbar"><ElButton
          type="primary"
          @click="addModel">新增模型</ElButton></div>
        <ElTable
          :data="models"
          stripe>
          <ElTableColumn
            prop="name"
            label="名称"
            min-width="140" />
          <ElTableColumn
            prop="provider"
            label="Provider"
            width="120" />
          <ElTableColumn
            prop="model"
            label="模型"
            min-width="160" />
          <ElTableColumn
            label="密钥"
            width="150"><template #default="{ row }">{{ row.api_key_masked || '未配置' }}</template></ElTableColumn>
          <ElTableColumn
            label="状态"
            width="110"><template #default="{ row }"><ElTag :type="row.enabled && row.enable_chat ? 'success' : 'info'">{{ row.enabled && row.enable_chat ? '可对话' : '已停用' }}</ElTag></template></ElTableColumn>
          <ElTableColumn
            label="操作"
            width="240"
            fixed="right">
            <template #default="{ row }">
              <ElButton
                link
                type="primary"
                @click="editModel(row)">编辑</ElButton>
              <ElButton
                link
                type="primary"
                @click="testModel(row)">连接测试</ElButton>
              <ElPopconfirm
                title="删除这个模型配置？"
                @confirm="deleteModel(row)"><template #reference><ElButton
                  link
                  type="danger">删除</ElButton></template></ElPopconfirm>
            </template>
          </ElTableColumn>
        </ElTable>
      </ElTabPane>

      <ElTabPane
        label="审计"
        name="audit">
        <div class="toolbar">
          <ElSelect
            v-model="auditQuery.status"
            clearable
            placeholder="全部状态"
            @change="loadAudits">
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
          <ElButton @click="loadAudits">刷新</ElButton>
        </div>
        <ElTable
          v-loading="loading"
          :data="audits"
          stripe
          @row-click="openAudit">
          <ElTableColumn
            prop="id"
            label="ID"
            width="80" />
          <ElTableColumn
            prop="conversation_id"
            label="会话"
            width="100" />
          <ElTableColumn
            prop="user_id"
            label="用户"
            width="100" />
          <ElTableColumn
            prop="model_id"
            label="模型"
            width="100" />
          <ElTableColumn
            label="状态"
            width="110"><template #default="{ row }"><ElTag :type="statusType(row.status)">{{ row.status }}</ElTag></template></ElTableColumn>
          <ElTableColumn
            prop="tool_call_count"
            label="工具调用"
            width="110" />
          <ElTableColumn
            prop="started_at"
            label="开始时间"
            min-width="180" />
          <ElTableColumn
            prop="error_message"
            label="错误摘要"
            min-width="220"
            show-overflow-tooltip />
        </ElTable>
        <ElPagination
          v-model:current-page="auditQuery.page"
          :page-size="auditQuery.size"
          :total="total"
          layout="prev, pager, next, total"
          @current-change="loadAudits" />
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
          <p>配置模型连接、生成参数和对话能力。</p>
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
          required><ElSelect v-model="form.provider"><ElOption
            v-for="provider in ['openai', 'openrouter', 'ollama', 'claude']"
            :key="provider"
            :label="provider"
            :value="provider" /></ElSelect></ElFormItem>
        <ElFormItem label="Base URL"><ElInput
          v-model="form.base_url"
          placeholder="留空使用 Provider 默认地址" /></ElFormItem>
        <ElFormItem label="API Key"><ElInput
          v-model="form.api_key"
          type="password"
          show-password
          :placeholder="editingId ? '留空表示不修改' : 'Ollama 可留空'" /></ElFormItem>
        <ElFormItem
          label="模型标识"
          required><ElInput v-model="form.model" /></ElFormItem>
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

<style scoped lang="scss">
.ai-center { padding-bottom: 24px; }
header { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 18px; }
.ai-center > header h2 { margin: 0 0 5px; font-size: 22px; color: var(--text-primary); }
.ai-center > header p { margin: 0; color: var(--text-secondary); }
.toolbar { display: flex; justify-content: flex-end; gap: 10px; margin: 8px 0 14px; }
.toolbar .el-select { width: 150px; }
.el-pagination { justify-content: flex-end; margin-top: 16px; }
</style>
