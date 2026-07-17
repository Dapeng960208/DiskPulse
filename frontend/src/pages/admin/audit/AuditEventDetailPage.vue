<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElButton, ElDescriptions, ElDescriptionsItem, ElEmpty, ElTag } from 'element-plus';
import auditEventsApi from '@/api/audit-events-api.js';
import { useBreadcrumbs } from '@/stores/breadcrumbs';

const route = useRoute();
const router = useRouter();
const breadcrumbs = useBreadcrumbs();
const event = ref(null);
const loading = ref(false);
const hasEvent = computed(() => Boolean(event.value));

function summary(value) {
  if (value == null || value === '') return '-';
  return typeof value === 'string' ? value : JSON.stringify(value, null, 2);
}

function outcomeType(outcome) {
  return { success: 'success', denied: 'warning', failure: 'danger' }[outcome] || 'info';
}

async function loadEvent() {
  loading.value = true;
  breadcrumbs.setDetailTitle(route.name, '');
  try {
    event.value = await auditEventsApi.fetchById(route.params.id);
    breadcrumbs.setDetailTitle(route.name, `审计事件 #${route.params.id}`);
  } catch {
    event.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(loadEvent);
</script>

<template>
  <section class="audit-event-detail-page">
    <div class="page-heading">
      <div>
        <h2>审计事件 #{{ route.params.id }}</h2>
        <p>仅展示经过后端脱敏的操作摘要。</p>
      </div>
      <ElButton @click="router.push('/admin/audit-events')">返回审计</ElButton>
    </div>
    <ElDescriptions
      v-if="hasEvent"
      v-loading="loading"
      :column="2"
      border>
      <ElDescriptionsItem label="发生时间">{{ event.occurred_at }}</ElDescriptionsItem>
      <ElDescriptionsItem label="结果"><ElTag :type="outcomeType(event.outcome)">{{ event.outcome }}</ElTag></ElDescriptionsItem>
      <ElDescriptionsItem label="操作">{{ event.action }}</ElDescriptionsItem>
      <ElDescriptionsItem label="原因码">{{ event.reason_code || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="主体">{{ event.actor?.rd_username || event.actor?.username || event.actor_user_id || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="项目">{{ event.project?.name || event.project_id || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="资源">{{ event.resource_type || '-' }}{{ event.resource_id == null ? '' : ` #${event.resource_id}` }}</ElDescriptionsItem>
      <ElDescriptionsItem label="关联标识">{{ event.trace_id || event.request_id || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem
        label="变更前摘要"
        :span="2"><pre>{{ summary(event.before_summary) }}</pre></ElDescriptionsItem>
      <ElDescriptionsItem
        label="变更后摘要"
        :span="2"><pre>{{ summary(event.after_summary) }}</pre></ElDescriptionsItem>
      <ElDescriptionsItem
        label="附加摘要"
        :span="2"><pre>{{ summary(event.metadata) }}</pre></ElDescriptionsItem>
    </ElDescriptions>
    <ElEmpty
      v-else-if="!loading"
      description="未找到审计事件" />
  </section>
</template>

<style scoped>
.audit-event-detail-page { display: grid; gap: var(--spacing-md); }
.page-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--spacing-md); }
.page-heading h2 { margin: 0 0 4px; color: var(--text-primary); font-size: var(--font-size-xl); }
.page-heading p { margin: 0; color: var(--text-secondary); }
pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: var(--font-size-sm); }
</style>
