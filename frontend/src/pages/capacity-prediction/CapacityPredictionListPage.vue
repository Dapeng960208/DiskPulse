<script setup>
import { onMounted, reactive, ref } from 'vue';
import { ElEmpty, ElTableColumn, ElTag } from 'element-plus';
import capacityPredictionApi from '@/api/capacity-prediction-api.js';
import DataTable from '@/components/data/DataTable.vue';
import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';

const predictions = ref([]);
const loading = ref(false);
const error = ref('');
const visible = ref(false);
const accessChecked = ref(false);
const pagination = reactive({ page: 1, pageSize: 20, total: 0 });
let querySequence = 0;

const assetTypeLabels = {
  group: '项目组',
  storage_usage: '用户目录',
};

function predictionSource(row) {
  return {
    ai_candidate: 'AI 候选',
    baseline_fallback: '基线回退',
    baseline: '内置基线',
  }[row.input_quality?.prediction_source] || '内置基线';
}

function detailTarget(row) {
  const id = Number(row.asset_id);
  if (!Number.isInteger(id) || id < 1) return null;
  if (row.asset_type === 'storage_usage') {
    return { name: 'UsageCapacityPrediction', params: { id } };
  }
  if (row.asset_type === 'group') {
    return { name: 'GroupCapacityPrediction', params: { id } };
  }
  return null;
}

async function query() {
  if (!visible.value) return;
  const requestSequence = ++querySequence;
  loading.value = true;
  error.value = '';
  try {
    const result = await capacityPredictionApi.fetchPredictions({
      page: pagination.page,
      size: pagination.pageSize,
    });
    if (requestSequence !== querySequence) return;
    predictions.value = result.content || [];
    pagination.total = Number(result.total) || 0;
  } catch {
    if (requestSequence !== querySequence) return;
    predictions.value = [];
    pagination.total = 0;
    error.value = '加载容量预测失败，请稍后重试';
  } finally {
    if (requestSequence === querySequence) loading.value = false;
  }
}

async function load() {
  try {
    const access = await capacityPredictionApi.visibility();
    visible.value = access.visible === true;
    if (visible.value) await query();
  } catch {
    visible.value = false;
  } finally {
    accessChecked.value = true;
  }
}

function updatePagination(next) {
  pagination.page = next.page;
  pagination.pageSize = next.pageSize;
  query();
}

onMounted(load);
</script>

<template>
  <section class="capacity-prediction-list-page">
    <DataTable
      v-if="visible"
      :data="predictions"
      :loading="loading"
      :error="error"
      :pagination="{
        page: pagination.page,
        pageSize: pagination.pageSize,
        total: pagination.total,
        pageSizes: [20, 50, 100],
        hideOnSinglePage: true,
        showJumper: true,
      }"
      @update:pagination="updatePagination">
      <ElTableColumn
        label="预测对象"
        min-width="220">
        <template #default="{ row }">
          <AccessibleResourceLink :to="detailTarget(row)">{{ row.display_name || '-' }}</AccessibleResourceLink>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="对象类型"
        width="140">
        <template #default="{ row }">{{ assetTypeLabels[row.asset_type] || row.asset_type }}</template>
      </ElTableColumn>
      <ElTableColumn
        label="P50 耗尽日期"
        width="160">
        <template #default="{ row }">{{ row.exhaustion_dates?.p50 || '30 天内无耗尽风险' }}</template>
      </ElTableColumn>
      <ElTableColumn
        label="预测来源"
        width="120">
        <template #default="{ row }"><ElTag :type="predictionSource(row) === '基线回退' ? 'warning' : 'info'">{{ predictionSource(row) }}</ElTag></template>
      </ElTableColumn>
      <ElTableColumn
        label="模型版本"
        min-width="150">
        <template #default="{ row }">
          {{ row.input_quality?.candidate_version || row.algorithm_version || '-' }}
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="生成时间"
        prop="created_at"
        min-width="190" />
    </DataTable>
    <ElEmpty
      v-else-if="accessChecked"
      description="容量预测未启用或当前账号无访问权限" />
  </section>
</template>

<style scoped>
.capacity-prediction-list-page { height: 100%; min-height: 0; }
</style>
