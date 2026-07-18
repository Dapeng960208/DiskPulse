<script setup>
import { onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import auditEventsApi from '@/api/audit-events-api.js';
import AuditEventTable from '@/components/audit/AuditEventTable.vue';

const props = defineProps({
  projectId: {
    type: Number,
    required: true,
  },
});

const events = ref([]);
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

onMounted(loadEvents);
</script>

<template>
  <section class="project-audit-tab">
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
.section-heading { margin-bottom: var(--spacing-md); }
.section-heading h3 { margin: 0 0 4px; color: var(--text-primary); font-size: var(--font-size-lg); }
.section-heading p { margin: 0; color: var(--text-secondary); font-size: var(--font-size-sm); }
</style>
