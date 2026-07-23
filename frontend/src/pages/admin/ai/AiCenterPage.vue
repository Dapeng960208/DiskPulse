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
  await loadModels();
  if (activeTab.value === 'audit') await loadAudits();
});
</script>

<template>
  <section class="ai-center">
    <ElTabs v-model="activeTab">
      <ElTabPane
        label="模型管理"
        name="models">
        <DataTable :data="models">
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
