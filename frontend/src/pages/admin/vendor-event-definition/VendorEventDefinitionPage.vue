<script setup>
import { onMounted, reactive, ref } from 'vue';
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTableColumn,
  ElTag,
} from 'element-plus';
import vendorEventDefinitionApi from '@/api/vendor-event-definition-api.js';
import TableActionButton from '@/components/basic/TableActionButton.vue';
import DataTable from '@/components/data/DataTable.vue';
import QueryForm from '@/components/form/QueryForm.vue';

const associationTypes = [
  { value: 'fault_log', label: '故障日志' },
  { value: 'performance_anomaly', label: '性能异常' },
  { value: 'capacity_threshold', label: '容量/配额阈值' },
  { value: 'system_activity', label: '系统运行事件' },
  { value: 'telemetry_degradation', label: '监控能力下降' },
  { value: 'unknown', label: '未分类厂商事件' },
];
const associationLabels = Object.fromEntries(associationTypes.map((item) => [item.value, item.label]));
const storageTypeLabels = { netapp: 'NetApp ONTAP', isilon: 'Dell PowerScale（Isilon）' };
const severityLabels = { critical: '严重', error: '错误', warning: '警告', info: '信息' };
const reviewLabels = { reviewed: '已审核', pending: '待审核' };

const rows = ref([]);
const total = ref(0);
const loading = ref(false);
const error = ref('');
const dialogVisible = ref(false);
const saving = ref(false);
const syncing = ref(false);
const editingId = ref(null);
const queryParams = reactive({
  page: 1,
  size: 20,
  storage_type: '',
  association_type: '',
  keyword: '',
  review_status: '',
});
const form = reactive({
  storage_type: 'netapp',
  event_code: '',
  association_type: 'unknown',
  title_zh: '',
  description_zh: '',
  official_reference_url: '',
  default_severity: '',
  version_scope: '',
  review_status: 'pending',
  is_active: true,
});

function requestParams() {
  return {
    page: queryParams.page,
    size: queryParams.size,
    ...(queryParams.storage_type ? { storage_type: queryParams.storage_type } : {}),
    ...(queryParams.association_type ? { association_type: queryParams.association_type } : {}),
    ...(queryParams.keyword.trim() ? { keyword: queryParams.keyword.trim() } : {}),
    ...(queryParams.review_status ? { review_status: queryParams.review_status } : {}),
  };
}

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const result = await vendorEventDefinitionApi.fetch(requestParams());
    rows.value = result?.content || [];
    total.value = Number(result?.total) || 0;
  } catch {
    rows.value = [];
    total.value = 0;
    error.value = '加载事件关联信息失败，请稍后重试';
  } finally {
    loading.value = false;
  }
}

function resetFilters() {
  Object.assign(queryParams, {
    page: 1,
    size: 20,
    storage_type: '',
    association_type: '',
    keyword: '',
    review_status: '',
  });
  load();
}

function resetForm() {
  Object.assign(form, {
    storage_type: 'netapp',
    event_code: '',
    association_type: 'unknown',
    title_zh: '',
    description_zh: '',
    official_reference_url: '',
    default_severity: '',
    version_scope: '',
    review_status: 'pending',
    is_active: true,
  });
}

function openEditor(row = null) {
  editingId.value = row?.id || null;
  resetForm();
  if (row) {
    Object.assign(form, {
      ...row,
      default_severity: row.default_severity || '',
      version_scope: row.version_scope || '',
      official_reference_url: row.official_reference_url || '',
      review_status: row.review_status || 'pending',
      is_active: row.is_active !== false,
    });
  }
  dialogVisible.value = true;
}

function formPayload() {
  return {
    storage_type: form.storage_type,
    event_code: form.event_code.trim(),
    association_type: form.association_type,
    title_zh: form.title_zh.trim(),
    description_zh: form.description_zh.trim(),
    official_reference_url: form.official_reference_url.trim() || null,
    default_severity: form.default_severity || null,
    version_scope: form.version_scope.trim() || null,
    review_status: form.review_status,
    is_active: form.is_active,
  };
}

async function save() {
  const payload = formPayload();
  if (!payload.event_code || !payload.title_zh || !payload.description_zh) {
    ElMessage.error('请填写事件代码、中文标题和中文含义');
    return;
  }
  saving.value = true;
  try {
    if (editingId.value) {
      await vendorEventDefinitionApi.update(editingId.value, payload);
    } else {
      await vendorEventDefinitionApi.create(payload);
    }
    dialogVisible.value = false;
    ElMessage.success(editingId.value ? '事件关联信息已更新' : '事件关联信息已新增');
    await load();
  } catch (requestError) {
    ElMessage.error(requestError?.response?.status === 409
      ? '该存储类型和事件代码已存在'
      : '保存事件关联信息失败，请稍后重试');
  } finally {
    saving.value = false;
  }
}

function remove(row) {
  ElMessageBox.confirm(`确认删除事件关联「${row.event_code}」？原始厂商日志不会被删除。`, '删除事件关联', {
    type: 'warning',
    confirmButtonText: '删除关联',
    cancelButtonText: '取消',
  })
    .then(() => vendorEventDefinitionApi.deleteById(row.id))
    .then(() => {
      ElMessage.success('事件关联信息已删除');
      load();
    })
    .catch((requestError) => {
      if (requestError !== 'cancel' && requestError !== 'close') {
        ElMessage.error('删除事件关联信息失败，请稍后重试');
      }
    });
}

async function discover() {
  syncing.value = true;
  try {
    const result = await vendorEventDefinitionApi.discover();
    ElMessage.success(
      `新增 ${result.created || 0} 个代码，已保留 ${result.existing || 0} 个；修复 ${result.reconciled_incidents || 0} 个历史误分类事件`,
    );
    await load();
  } catch {
    ElMessage.error('同步已采集事件代码失败，请稍后重试');
  } finally {
    syncing.value = false;
  }
}

function updatePagination(next) {
  queryParams.page = next.page;
  queryParams.size = next.pageSize;
  load();
}

onMounted(load);
</script>

<template>
  <section class="vendor-event-definition-page">
    <QueryForm
      @query="queryParams.page = 1; load()"
      @reset="resetFilters">
      <ElFormItem label="存储类型">
        <ElSelect
          v-model="queryParams.storage_type"
          clearable
          placeholder="全部存储类型">
          <ElOption
            label="NetApp ONTAP"
            value="netapp" />
          <ElOption
            label="Dell PowerScale（Isilon）"
            value="isilon" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem label="关联类型">
        <ElSelect
          v-model="queryParams.association_type"
          clearable
          placeholder="全部关联类型">
          <ElOption
            v-for="item in associationTypes"
            :key="item.value"
            :label="item.label"
            :value="item.value" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem label="事件代码或中文含义">
        <ElInput
          v-model="queryParams.keyword"
          clearable
          placeholder="搜索事件代码、标题或含义" />
      </ElFormItem>
      <ElFormItem label="审核状态">
        <ElSelect
          v-model="queryParams.review_status"
          clearable
          placeholder="全部审核状态">
          <ElOption
            label="已审核"
            value="reviewed" />
          <ElOption
            label="待审核"
            value="pending" />
        </ElSelect>
      </ElFormItem>
      <template #actions>
        <TableActionButton
          data-testid="event-association-sync"
          action="sync"
          :loading="syncing"
          @click="discover">同步已采集代码</TableActionButton>
      </template>
    </QueryForm>

    <DataTable
      class="vendor-event-definition-page__table"
      :data="rows"
      :loading="loading"
      :error="error"
      :pagination="{ page: queryParams.page, pageSize: queryParams.size, total, pageSizes: [20, 50, 100], hideOnSinglePage: true, showJumper: true }"
      @update:pagination="updatePagination">
      <ElTableColumn
        label="存储类型"
        min-width="170">
        <template #default="{ row }">{{ storageTypeLabels[row.storage_type] || row.storage_type }}</template>
      </ElTableColumn>
      <ElTableColumn
        label="事件代码"
        prop="event_code"
        min-width="230"
        show-overflow-tooltip />
      <ElTableColumn
        label="关联类型"
        min-width="150">
        <template #default="{ row }">
          <ElTag :type="row.association_type === 'fault_log' ? 'danger' : row.association_type === 'performance_anomaly' ? 'warning' : 'info'">
            {{ associationLabels[row.association_type] || row.association_type }}
          </ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="中文标题"
        prop="title_zh"
        min-width="190" />
      <ElTableColumn
        label="中文含义"
        prop="description_zh"
        min-width="300"
        show-overflow-tooltip />
      <ElTableColumn
        label="默认等级"
        width="110">
        <template #default="{ row }">{{ severityLabels[row.default_severity] || '采用实例等级' }}</template>
      </ElTableColumn>
      <ElTableColumn
        label="审核状态"
        width="105">
        <template #default="{ row }">
          <ElTag :type="row.review_status === 'reviewed' ? 'success' : 'warning'">
            {{ reviewLabels[row.review_status] || row.review_status }}
          </ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="状态"
        width="90">
        <template #default="{ row }">
          <ElTag :type="row.is_active === false ? 'info' : 'success'">{{ row.is_active === false ? '停用' : '启用' }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        align="right"
        fixed="right"
        width="170">
        <template #header>
          <TableActionButton
            data-testid="event-association-create"
            action="create"
            @click="openEditor()">新增关联</TableActionButton>
        </template>
        <template #default="{ row }">
          <TableActionButton
            :data-testid="`event-association-edit-${row.id}`"
            action="edit"
            @click="openEditor(row)">编辑</TableActionButton>
          <TableActionButton
            :data-testid="`event-association-delete-${row.id}`"
            action="delete"
            @click="remove(row)">删除</TableActionButton>
        </template>
      </ElTableColumn>
    </DataTable>

    <ElDialog
      v-model="dialogVisible"
      :title="editingId ? '编辑事件关联信息' : '新增事件关联信息'"
      width="min(720px, 96vw)">
      <ElForm label-position="top">
        <div class="vendor-event-definition-form__grid">
          <ElFormItem
            label="存储类型"
            required>
            <ElSelect v-model="form.storage_type">
              <ElOption
                label="NetApp ONTAP"
                value="netapp" />
              <ElOption
                label="Dell PowerScale（Isilon）"
                value="isilon" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem
            label="事件代码"
            required>
            <ElInput
              v-model="form.event_code"
              maxlength="255"
              placeholder="例如 secd.authsys.lookup.failed" />
          </ElFormItem>
          <ElFormItem
            label="关联类型"
            required>
            <ElSelect v-model="form.association_type">
              <ElOption
                v-for="item in associationTypes"
                :key="item.value"
                :label="item.label"
                :value="item.value" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="默认等级">
            <ElSelect
              v-model="form.default_severity"
              clearable
              placeholder="采用事件实例等级">
              <ElOption
                label="严重"
                value="critical" />
              <ElOption
                label="错误"
                value="error" />
              <ElOption
                label="警告"
                value="warning" />
              <ElOption
                label="信息"
                value="info" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem
            label="中文标题"
            required>
            <ElInput
              v-model="form.title_zh"
              maxlength="255" />
          </ElFormItem>
          <ElFormItem
            label="审核状态"
            required>
            <ElSelect v-model="form.review_status">
              <ElOption
                label="已审核"
                value="reviewed" />
              <ElOption
                label="待审核"
                value="pending" />
            </ElSelect>
          </ElFormItem>
        </div>
        <ElFormItem
          label="中文含义"
          required>
          <ElInput
            v-model="form.description_zh"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit />
        </ElFormItem>
        <ElFormItem label="官方参考地址">
          <ElInput
            v-model="form.official_reference_url"
            maxlength="1000"
            placeholder="厂商官方文档 HTTPS 地址" />
        </ElFormItem>
        <ElFormItem label="适用版本">
          <ElInput
            v-model="form.version_scope"
            maxlength="255"
            placeholder="例如 ONTAP 9.11.1–9.18.1" />
        </ElFormItem>
        <ElFormItem label="启用状态">
          <ElSwitch
            v-model="form.is_active"
            active-text="启用"
            inactive-text="停用" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="saving"
          @click="save">保存</ElButton>
      </template>
    </ElDialog>
  </section>
</template>

<style scoped>
.vendor-event-definition-page { display: flex; flex: 1; min-height: 0; flex-direction: column; gap: var(--spacing-md); }
.vendor-event-definition-page__table { min-height: 480px; }
.vendor-event-definition-form__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 var(--spacing-md); }
@media (max-width: 720px) { .vendor-event-definition-form__grid { grid-template-columns: 1fr; } }
</style>
