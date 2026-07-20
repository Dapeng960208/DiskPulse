<script setup>
import { onMounted, reactive, ref, watch } from 'vue';
import { ElButton, ElFormItem, ElOption, ElPagination, ElSelect, ElTable, ElTableColumn, ElTag } from 'element-plus';
import incidentApi from '@/api/incident-api.js';
import IncidentDetailDrawer from '@/pages/incident/components/IncidentDetailDrawer.vue';
import TableActionButton from '@/components/basic/TableActionButton.vue';
import QueryForm from '@/components/form/QueryForm.vue';
import { useResponsiveTableColumns } from '@/composables/responsive-table-columns';

const props = defineProps({
  clusterId: { type: Number, required: true },
});

const incidents = ref([]);
const total = ref(0);
const page = ref(1);
const size = ref(20);
const loading = ref(false);
const forecastCount = ref(0);
const anomalyCount = ref(0);
const selectedIncident = ref(null);
const detailVisible = ref(false);
const filters = reactive({ status: '', category: '' });
const { showCapacityColumns, showSecondaryColumns } = useResponsiveTableColumns();

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

async function load(reset = false) {
  if (!props.clusterId) return;
  if (reset) page.value = 1;
  loading.value = true;
  try {
    const params = {
      storage_cluster_id: props.clusterId,
      ...(filters.status ? { status: filters.status } : {}),
      ...(filters.category ? { category: filters.category } : {}),
      page: page.value,
      size: size.value,
    };
    const [result, forecasts, anomalies] = await Promise.all([
      incidentApi.fetchIncidents(params),
      incidentApi.fetchForecasts({ storage_cluster_id: props.clusterId, page: 1, size: 5 }),
      incidentApi.fetchAnomalies({ storage_cluster_id: props.clusterId, page: 1, size: 5 }),
    ]);
    incidents.value = sortLatestEvidence(result.content || []);
    total.value = Number(result.total) || 0;
    forecastCount.value = Number(forecasts.total) || 0;
    anomalyCount.value = Number(anomalies.total) || 0;
  } catch {
    incidents.value = [];
    total.value = 0;
    forecastCount.value = 0;
    anomalyCount.value = 0;
  } finally {
    loading.value = false;
  }
}

function openDetail(incident) {
  selectedIncident.value = incident;
  detailVisible.value = true;
}

function queryWithFilters() {
  load(true);
}

function resetFilters() {
  filters.status = '';
  filters.category = '';
  load(true);
}

watch(() => props.clusterId, () => load(true));
onMounted(load);
</script>

<template>
  <section class="cluster-incidents-tab">
    <QueryForm
      @query="queryWithFilters"
      @reset="resetFilters">
      <ElFormItem label="状态">
        <ElSelect
          v-model="filters.status"
          clearable
          placeholder="全部状态">
          <ElOption
            label="未处理"
            value="open" />
          <ElOption
            label="已确认"
            value="acknowledged" />
          <ElOption
            label="调查中"
            value="investigating" />
          <ElOption
            label="已缓解"
            value="mitigated" />
          <ElOption
            label="已解决"
            value="resolved" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem label="事件类型">
        <ElSelect
          v-model="filters.category"
          clearable
          placeholder="全部类型">
          <ElOption
            label="容量压力"
            value="capacity_pressure" />
          <ElOption
            label="设备健康风险"
            value="device_fault" />
          <ElOption
            label="性能争用"
            value="performance_contention" />
          <ElOption
            label="监控盲区"
            value="telemetry_blindspot" />
        </ElSelect>
      </ElFormItem>
    </QueryForm>
    <p class="cluster-incidents-tab__intro">仅显示当前存储集群关联的项目范围事件；原始告警和厂商系统事件仍位于原有页面。</p>
    <dl
      class="cluster-incidents-tab__summary"
      aria-label="关联健康分析摘要">
      <div><dt>关联事件</dt><dd>{{ total }}</dd></div>
      <div><dt>容量预测</dt><dd>{{ forecastCount }}</dd></div>
      <div><dt>性能异常</dt><dd>{{ anomalyCount }}</dd></div>
    </dl>
    <ElTable
      v-loading="loading"
      :data="incidents"
      empty-text="暂无关联事件">
      <ElTableColumn
        label="受影响对象"
        prop="display_name"
        min-width="180" />
      <ElTableColumn
        label="事件类型"
        prop="category"
        min-width="160" />
      <ElTableColumn
        label="严重度"
        prop="severity"
        width="110">
        <template #default="{ row }"><ElTag :type="row.severity === 'critical' ? 'danger' : 'warning'">{{ row.severity }}</ElTag></template>
      </ElTableColumn>
      <ElTableColumn
        v-if="showCapacityColumns"
        label="状态"
        prop="status"
        width="130" />
      <ElTableColumn
        v-if="showSecondaryColumns"
        label="最近证据"
        min-width="190">
        <template #default="{ row }">
          <time :datetime="row.last_evidence_at">{{ formatLocalDateTime(row.last_evidence_at) }}</time>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="详情"
        align="right"
        width="90"
        fixed="right">
        <template #default="{ row }"><TableActionButton
          action="detail"
          @click="openDetail(row)">查看</TableActionButton></template>
      </ElTableColumn>
    </ElTable>
    <ElPagination
      v-if="total > 0"
      class="cluster-incidents-tab__pagination"
      background
      layout="total, sizes, prev, pager, next"
      :current-page="page"
      :page-size="size"
      :page-sizes="[20, 50, 100]"
      :total="total"
      @current-change="(value) => { page = value; load(); }"
      @size-change="(value) => { size = value; load(true); }" />
    <IncidentDetailDrawer
      v-model="detailVisible"
      :incident="selectedIncident"
      @updated="load" />
  </section>
</template>

<style scoped>
.cluster-incidents-tab__intro { margin: 0 0 var(--spacing-md); color: var(--text-secondary); }
.cluster-incidents-tab__summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 0 0 var(--spacing-md); }
.cluster-incidents-tab__summary div { padding: 12px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-secondary); }
.cluster-incidents-tab__summary dt { color: var(--text-secondary); font-size: var(--font-size-sm); }
.cluster-incidents-tab__summary dd { margin: 4px 0 0; color: var(--text-primary); font-size: var(--font-size-lg); font-weight: 600; }
.cluster-incidents-tab__pagination { display: flex; justify-content: flex-end; margin-top: var(--spacing-md); }
.cluster-incidents-tab :deep(.el-table__body-wrapper) { overflow-x: hidden !important; }
.cluster-incidents-tab :deep(.el-table .cell) { overflow-wrap: anywhere; white-space: normal; }
@media (max-width: 640px) { .cluster-incidents-tab__summary { grid-template-columns: 1fr; } }
</style>
