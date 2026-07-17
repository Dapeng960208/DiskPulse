<script setup>
import { onMounted, ref } from 'vue';
import { ElDatePicker, ElFormItem, ElInput, ElOption, ElSelect } from 'element-plus';
import { useRouter } from 'vue-router';
import auditEventsApi from '@/api/audit-events-api.js';
import AuditEventTable from '@/components/audit/AuditEventTable.vue';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import QueryForm from '@/components/form/QueryForm.vue';
import RdUserSelect from '@/components/form/RdUserSelect.vue';
import { useQueryParams } from '@/composables/query';

const router = useRouter();
const { queryParams, reset } = useQueryParams(() => ({ page: 1, size: 20 }));
const timeRange = ref([]);
const events = ref([]);
const total = ref(0);
const loading = ref(false);
const error = ref('');

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
  router.push(`/admin/audit-events/${event.id}`);
}

onMounted(query);
</script>

<template>
  <section class="audit-event-list-page">
    <header class="page-heading">
      <div>
        <h2>统一操作审计</h2>
        <p>查询跨项目的脱敏操作记录和关联标识。</p>
      </div>
    </header>
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
        <ElDatePicker
          v-model="timeRange"
          type="datetimerange"
          value-format="YYYY-MM-DD HH:mm:ss"
          start-placeholder="开始时间"
          end-placeholder="结束时间" />
      </ElFormItem>
    </QueryForm>
    <AuditEventTable
      class="audit-event-list-page__table"
      :events="events"
      :loading="loading"
      :error="error"
      :pagination="{ page: queryParams.page, pageSize: queryParams.size, total, pageSizes: [20, 50, 100], showJumper: true }"
      show-details
      @update:pagination="updatePagination"
      @show-detail="showDetail" />
  </section>
</template>

<style scoped>
.audit-event-list-page { display: grid; gap: var(--spacing-md); }
.page-heading h2 { margin: 0 0 4px; color: var(--text-primary); font-size: var(--font-size-xl); }
.page-heading p { margin: 0; color: var(--text-secondary); }
.audit-event-list-page__table { min-height: 420px; }
</style>
