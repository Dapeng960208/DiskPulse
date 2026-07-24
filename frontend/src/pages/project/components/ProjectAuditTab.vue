<script setup>
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElButton, ElMessage } from 'element-plus';
import auditEventsApi from '@/api/audit-events-api.js';
import AuditEventTable from '@/components/audit/AuditEventTable.vue';

const props = defineProps({
  projectId: {
    type: Number,
    required: true,
  },
});

const events = ref([]);
const router = useRouter();
const total = ref(0);
const loading = ref(false);
const error = ref('');
const pagination = ref({ page: 1, pageSize: 20, total: 0, hideOnSinglePage: true, showJumper: true });

async function loadEvents() {
  loading.value = true;
  error.value = '';
  try {
    const result = await auditEventsApi.fetch({
      project_id: props.projectId,
      page: pagination.value.page,
      size: pagination.value.pageSize,
    });
    events.value = result.content || [];
    total.value = result.total || 0;
    pagination.value = { ...pagination.value, total: total.value };
  } catch {
    events.value = [];
    error.value = '加载项目审计失败，请稍后重试';
    ElMessage.error(error.value);
  } finally {
    loading.value = false;
  }
}

function updatePagination(next) {
  pagination.value = { ...pagination.value, ...next };
  loadEvents();
}

function analyzeProjectAudit() {
  if (!Number.isInteger(props.projectId) || props.projectId < 1) return;
  router.push({ name: 'AIChat', query: { audit_project_id: String(props.projectId) } });
}

onMounted(loadEvents);
</script>

<template>
  <section class="project-audit-tab">
    <div class="project-audit-tab__actions">
      <ElButton
        plain
        type="primary"
        @click="analyzeProjectAudit">AI 研判本项目审计</ElButton>
    </div>
    <AuditEventTable
      :events="events"
      :loading="loading"
      :error="error"
      :pagination="pagination"
      :show-project="false"
      @update:pagination="updatePagination" />
  </section>
</template>

<style scoped>
.project-audit-tab {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.project-audit-tab__actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--spacing-sm);
}

.project-audit-tab :deep(.data-table-card) {
  flex: 1 1 auto;
  min-height: 0;
  height: auto;
}
</style>
