<script setup>
import { onMounted, reactive, ref } from 'vue';
import {
  ElButton,
  ElCard,
  ElFormItem,
  ElInput,
  ElOption,
  ElPagination,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';
import QueryForm from '@/components/form/QueryForm.vue';
import incidentApi from '@/api/incident-api.js';

const queryParams = reactive({ page: 1, size: 20, status: '', category: '' });
const incidents = ref([]);
const total = ref(0);
const loading = ref(false);
const error = ref('');

const statusLabels = {
  open: '未处理',
  acknowledged: '已确认',
  investigating: '调查中',
  mitigated: '已缓解',
  resolved: '已解决',
};

const categoryLabels = {
  capacity_pressure: '容量压力',
  device_fault: '设备故障',
  performance_contention: '性能争用',
  telemetry_blindspot: '遥测盲区',
};

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

function updatePage(page) {
  queryParams.page = page;
  query();
}

function updateSize(size) {
  queryParams.size = size;
  queryParams.page = 1;
  query();
}

onMounted(query);
</script>

<template>
  <section class="incident-center-page">
    <header class="page-heading">
      <div>
        <h2>事件中心</h2>
        <p>集中查看项目范围内的容量、性能、设备与遥测关联事件。</p>
      </div>
    </header>
    <QueryForm
      @query="{ queryParams.page = 1; query(); }"
      @reset="reset">
      <ElFormItem label="状态">
        <ElSelect v-model="queryParams.status" clearable placeholder="全部状态">
          <ElOption v-for="(label, value) in statusLabels" :key="value" :label="label" :value="value" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem label="类别">
        <ElSelect v-model="queryParams.category" clearable placeholder="全部类别">
          <ElOption v-for="(label, value) in categoryLabels" :key="value" :label="label" :value="value" />
        </ElSelect>
      </ElFormItem>
      <template #actions>
        <ElButton type="primary" @click="query">搜索</ElButton>
      </template>
    </QueryForm>
    <ElCard class="incident-center-page__table">
      <p v-if="error" class="incident-center-page__error">{{ error }}</p>
      <ElTable v-loading="loading" :data="incidents" empty-text="当前项目范围内暂无事件">
        <ElTableColumn label="资产" prop="display_name" min-width="180" />
        <ElTableColumn label="类别" min-width="120">
          <template #default="{ row }">{{ categoryLabels[row.category] || row.category }}</template>
        </ElTableColumn>
        <ElTableColumn label="严重度" prop="severity" width="110">
          <template #default="{ row }"><ElTag :type="row.severity === 'critical' ? 'danger' : 'warning'">{{ row.severity }}</ElTag></template>
        </ElTableColumn>
        <ElTableColumn label="状态" width="120">
          <template #default="{ row }">{{ statusLabels[row.status] || row.status }}</template>
        </ElTableColumn>
        <ElTableColumn label="最近证据" prop="last_evidence_at" min-width="190" />
      </ElTable>
      <ElPagination
        v-if="total > 0"
        class="incident-center-page__pagination"
        background
        layout="total, sizes, prev, pager, next, jumper"
        :current-page="queryParams.page"
        :page-size="queryParams.size"
        :page-sizes="[20, 50, 100]"
        :total="total"
        @current-change="updatePage"
        @size-change="updateSize" />
    </ElCard>
  </section>
</template>

<style scoped>
.incident-center-page { display: grid; gap: var(--spacing-md); }
.page-heading h2 { margin: 0 0 4px; color: var(--text-primary); font-size: var(--font-size-xl); }
.page-heading p { margin: 0; color: var(--text-secondary); }
.incident-center-page__table { min-height: 420px; }
.incident-center-page__pagination { display: flex; justify-content: flex-end; margin-top: var(--spacing-md); }
.incident-center-page__error { margin: 0 0 var(--spacing-md); color: var(--danger-color); }
</style>
