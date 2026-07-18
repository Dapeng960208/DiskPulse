<script setup>
import { onMounted, ref, watch } from 'vue';
import { ElPagination, ElTable, ElTableColumn, ElTag } from 'element-plus';
import incidentApi from '@/api/incident-api.js';

const props = defineProps({
  clusterId: { type: Number, required: true },
});

const incidents = ref([]);
const total = ref(0);
const page = ref(1);
const size = ref(20);
const loading = ref(false);

async function load(reset = false) {
  if (!props.clusterId) return;
  if (reset) page.value = 1;
  loading.value = true;
  try {
    const result = await incidentApi.fetchIncidents({
      storage_cluster_id: props.clusterId,
      page: page.value,
      size: size.value,
    });
    incidents.value = result.content || [];
    total.value = Number(result.total) || 0;
  } catch {
    incidents.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

watch(() => props.clusterId, () => load(true));
onMounted(load);
</script>

<template>
  <section class="cluster-incidents-tab">
    <p class="cluster-incidents-tab__intro">仅显示当前存储集群关联的项目范围事件；原始告警和厂商系统事件仍位于原有页面。</p>
    <ElTable v-loading="loading" :data="incidents" empty-text="暂无关联事件">
      <ElTableColumn label="资产" prop="display_name" min-width="180" />
      <ElTableColumn label="类别" prop="category" min-width="160" />
      <ElTableColumn label="严重度" prop="severity" width="110">
        <template #default="{ row }"><ElTag :type="row.severity === 'critical' ? 'danger' : 'warning'">{{ row.severity }}</ElTag></template>
      </ElTableColumn>
      <ElTableColumn label="状态" prop="status" width="130" />
      <ElTableColumn label="最近证据" prop="last_evidence_at" min-width="190" />
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
  </section>
</template>

<style scoped>
.cluster-incidents-tab__intro { margin: 0 0 var(--spacing-md); color: var(--text-secondary); }
.cluster-incidents-tab__pagination { display: flex; justify-content: flex-end; margin-top: var(--spacing-md); }
</style>
