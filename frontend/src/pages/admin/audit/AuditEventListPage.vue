<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElButton, ElFormItem, ElInput, ElOption, ElSelect } from 'element-plus';
import auditEventsApi from '@/api/audit-events-api.js';
import AuditEventTable from '@/components/audit/AuditEventTable.vue';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import QueryForm from '@/components/form/QueryForm.vue';
import RdUserSelect from '@/components/form/RdUserSelect.vue';
import TimeRangePicker from '@/components/form/TimeRangePicker.vue';
import { useQueryParams } from '@/composables/query';
import AuditEventDetailDrawer from './components/AuditEventDetailDrawer.vue';

const { queryParams, reset } = useQueryParams(() => ({ page: 1, size: 20 }));
const router = useRouter();
const timeRange = ref([]);
const events = ref([]);
const total = ref(0);
const loading = ref(false);
const error = ref('');
const selectedEvent = ref(null);
const detailVisible = ref(false);
const hasCompleteTimeRange = computed(() => {
  const [startTime, endTime] = timeRange.value || [];
  return Boolean(startTime && endTime);
});
const canAnalyzeCurrentFilters = computed(() => Boolean(queryParams.value.project_id) || hasCompleteTimeRange.value);

async function query() {
  loading.value = true;
  error.value = '';
  const [start_time, end_time] = timeRange.value || [];
  try {
    const result = await auditEventsApi.fetch({
      ...queryParams.value,
      action: queryParams.value.action || undefined,
      actor_user_id: queryParams.value.actor_user_id || undefined,
      outcome: queryParams.value.outcome || undefined,
      project_id: queryParams.value.project_id || undefined,
      start_time,
      end_time,
    });
    events.value = result.content || [];
    total.value = result.total || 0;
  } catch {
    events.value = [];
    error.value = '加载统一操作审计失败，请稍后重试';
  } finally {
    loading.value = false;
  }
}

function resetFilters() {
  reset();
  timeRange.value = [];
  query();
}

function updatePagination(next) {
  queryParams.value.page = next.page;
  queryParams.value.size = next.pageSize;
  query();
}

function showDetail(event) {
  selectedEvent.value = event;
  detailVisible.value = true;
}

function auditFilterHandoffQuery() {
  const [startTime, endTime] = timeRange.value || [];
  return {
    ...(queryParams.value.project_id ? { audit_project_id: String(queryParams.value.project_id) } : {}),
    ...(queryParams.value.actor_user_id ? { audit_actor_user_id: String(queryParams.value.actor_user_id) } : {}),
    ...(queryParams.value.action ? { audit_action: queryParams.value.action } : {}),
    ...(queryParams.value.outcome ? { audit_outcome: queryParams.value.outcome } : {}),
    ...(startTime && endTime ? { audit_start_time: startTime, audit_end_time: endTime } : {}),
  };
}

function analyzeCurrentFilters() {
  if (!canAnalyzeCurrentFilters.value) return;
  router.push({ name: 'AIChat', query: auditFilterHandoffQuery() });
}

function analyzeEvent(event) {
  if (!event?.id) return;
  router.push({ name: 'AIChat', query: { audit_event_id: String(event.id) } });
}

onMounted(query);
</script>

<template>
  <section class="audit-event-list-page">
    <QueryForm
      @query="{
        queryParams.page = 1;
        query();
      }"
      @reset="resetFilters">
      <ElFormItem label="项目">
        <ProjectSelect
          v-model="queryParams.project_id"
          clearable />
      </ElFormItem>
      <ElFormItem label="用户">
        <RdUserSelect
          v-model="queryParams.actor_user_id"
          clearable />
      </ElFormItem>
      <ElFormItem label="操作">
        <ElInput
          v-model="queryParams.action"
          clearable
          placeholder="例如 quota.adjust" />
      </ElFormItem>
      <ElFormItem label="结果">
        <ElSelect
          v-model="queryParams.outcome"
          clearable
          placeholder="全部结果">
          <ElOption
            label="成功"
            value="success" />
          <ElOption
            label="拒绝"
            value="denied" />
          <ElOption
            label="失败"
            value="failure" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem
        class="query-form-field--date-range"
        label="发生时间">
        <TimeRangePicker v-model="timeRange" />
      </ElFormItem>
      <template #actions>
        <ElButton
          plain
          :disabled="!canAnalyzeCurrentFilters"
          @click="analyzeCurrentFilters">AI 研判当前筛选</ElButton>
      </template>
    </QueryForm>
    <AuditEventTable
      class="audit-event-list-page__table"
      :events="events"
      :loading="loading"
      :error="error"
      :pagination="{ page: queryParams.page, pageSize: queryParams.size, total, pageSizes: [20, 50, 100], hideOnSinglePage: true, showJumper: true }"
      show-details
      @update:pagination="updatePagination"
      @show-detail="showDetail" />
    <AuditEventDetailDrawer
      v-model="detailVisible"
      :event="selectedEvent"
      @analyze="analyzeEvent" />
  </section>
</template>

<style scoped>
.audit-event-list-page { display: flex; flex-direction: column; gap: var(--spacing-md); }
.audit-event-list-page__table { min-height: 420px; }
</style>
