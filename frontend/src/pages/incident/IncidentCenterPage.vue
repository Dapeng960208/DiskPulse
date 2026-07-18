<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
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
    incidents.value = result.content || [];
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
        label="状态"
        width="120">
        <template #default="{ row }">{{ statusLabels[row.status] || row.status }}</template>
      </ElTableColumn>
      <ElTableColumn
        label="最近证据"
        prop="last_evidence_at"
        min-width="190" />
      <ElTableColumn
        label="操作"
        align="right"
        width="150"
        fixed="right">
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
  </section>
</template>

<style scoped>
.incident-center-page { display: flex; flex-direction: column; gap: var(--spacing-md); }
.incident-center-page__table { min-height: 420px; }
</style>
