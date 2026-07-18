<script setup>
import { onMounted, ref, watch } from 'vue';
import { ElButton, ElPagination, ElTable, ElTableColumn, ElTag } from 'element-plus';
import incidentApi from '@/api/incident-api.js';
import IncidentDetailDrawer from '@/pages/incident/components/IncidentDetailDrawer.vue';

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

async function load(reset = false) {
  if (!props.clusterId) return;
  if (reset) page.value = 1;
  loading.value = true;
  try {
    const params = {
      storage_cluster_id: props.clusterId,
      page: page.value,
      size: size.value,
    };
    const [result, forecasts, anomalies] = await Promise.all([
      incidentApi.fetchIncidents(params),
      incidentApi.fetchForecasts({ storage_cluster_id: props.clusterId, page: 1, size: 5 }),
      incidentApi.fetchAnomalies({ storage_cluster_id: props.clusterId, page: 1, size: 5 }),
    ]);
    incidents.value = result.content || [];
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

watch(() => props.clusterId, () => load(true));
onMounted(load);
</script>

<template>
  <section class="cluster-incidents-tab">
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
        label="资产"
        prop="display_name"
        min-width="180" />
      <ElTableColumn
        label="类别"
        prop="category"
        min-width="160" />
      <ElTableColumn
        label="严重度"
        prop="severity"
        width="110">
        <template #default="{ row }"><ElTag :type="row.severity === 'critical' ? 'danger' : 'warning'">{{ row.severity }}</ElTag></template>
      </ElTableColumn>
      <ElTableColumn
        label="状态"
        prop="status"
        width="130" />
      <ElTableColumn
        label="最近证据"
        prop="last_evidence_at"
        min-width="190" />
      <ElTableColumn
        label="详情"
        align="right"
        width="90"
        fixed="right">
        <template #default="{ row }"><ElButton
          size="small"
          @click="openDetail(row)">查看</ElButton></template>
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
@media (max-width: 640px) { .cluster-incidents-tab__summary { grid-template-columns: 1fr; } }
</style>
