<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElButton, ElDescriptions, ElDescriptionsItem, ElEmpty, ElTag } from 'element-plus';
import auditEventsApi from '@/api/audit-events-api.js';
import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';
import { useBreadcrumbs } from '@/stores/breadcrumbs';
import {
  auditActionDescription,
  auditActorTypeLabel,
  auditOutcomeLabel,
  auditPhaseLabel,
  auditRequesterLabel,
  formatAuditOccurredAt,
} from '@/utils/audit-event-display.js';

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

function resourceName(current) {
  const resource = current.resource;
  const resourceType = resource?.type || current.resource_type;
  const typeLabel = {
    group: '项目组',
    project: '项目',
    project_membership: '项目成员',
    qtree: 'Qtree',
    storage_alert: '存储告警',
    storage_cluster: '存储集群',
    storage_usage: '用户目录',
    user: '用户',
    volume: '存储空间',
  }[resourceType] || resourceType || '-';
  if (resource?.name) return `${typeLabel} · ${resource.name}`;
  return current.resource_id == null ? typeLabel : `${typeLabel} #${current.resource_id}`;
}

function resourceRoute(current) {
  const resource = current.resource || { type: current.resource_type, id: current.resource_id };
  const name = {
    group: 'GroupDetail',
    project: 'ProjectDetail',
    qtree: 'QtreeDetail',
    storage_cluster: 'StorageClusterDetail',
    storage_usage: 'UsagesDetail',
    volume: 'VolumeDetail',
  }[resource.type];
  return name && resource.id != null ? { name, params: { id: resource.id } } : null;
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

function analyzeEvent() {
  if (!event.value?.id) return;
  router.push({ name: 'AIChat', query: { audit_event_id: String(event.value.id) } });
}

onMounted(loadEvent);
</script>

<template>
  <section class="audit-event-detail-page">
    <div class="page-heading">
      <div>
        <h2>审计事件 #{{ route.params.id }}</h2>
      </div>
      <div class="page-heading__actions">
        <ElButton
          :disabled="!hasEvent"
          type="primary"
          @click="analyzeEvent">AI 研判</ElButton>
        <ElButton @click="router.push('/admin/audit-events')">返回审计</ElButton>
      </div>
    </div>
    <ElDescriptions
      v-if="hasEvent"
      v-loading="loading"
      :column="2"
      border>
      <ElDescriptionsItem label="发生时间">{{ formatAuditOccurredAt(event.occurred_at) }}</ElDescriptionsItem>
      <ElDescriptionsItem label="结果"><ElTag :type="outcomeType(event.outcome)">{{ auditOutcomeLabel(event.outcome) }}</ElTag></ElDescriptionsItem>
      <ElDescriptionsItem label="操作">{{ auditActionDescription(event.action) }}</ElDescriptionsItem>
      <ElDescriptionsItem label="记录阶段">{{ auditPhaseLabel(event.phase) }}</ElDescriptionsItem>
      <ElDescriptionsItem label="原因码">{{ event.reason_code || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="请求/触发方">{{ auditRequesterLabel(event) }}</ElDescriptionsItem>
      <ElDescriptionsItem label="执行来源">{{ auditActorTypeLabel(event.actor_type) }}</ElDescriptionsItem>
      <ElDescriptionsItem label="项目"><AccessibleResourceLink :to="{ name: 'ProjectDetail', params: { id: event.project?.id } }">{{ event.project?.name || event.project_id || '-' }}</AccessibleResourceLink></ElDescriptionsItem>
      <ElDescriptionsItem label="资源"><AccessibleResourceLink :to="resourceRoute(event)">{{ resourceName(event) }}</AccessibleResourceLink></ElDescriptionsItem>
      <ElDescriptionsItem label="关联项目">
        <div
          v-if="event.related_projects?.length"
          class="audit-event-detail-page__project-links">
          <AccessibleResourceLink
            v-for="project in event.related_projects"
            :key="project.id"
            :to="{ name: 'ProjectDetail', params: { id: project.id } }">{{ project.name }}</AccessibleResourceLink>
        </div>
        <span v-else>无项目关联</span>
      </ElDescriptionsItem>
      <ElDescriptionsItem label="关联路径">{{ event.relation_path || '-' }}</ElDescriptionsItem>
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
.page-heading__actions { display: flex; gap: var(--spacing-sm); }
.page-heading h2 { margin: 0 0 4px; color: var(--text-primary); font-size: var(--font-size-xl); }
.page-heading p { margin: 0; color: var(--text-secondary); }
pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: var(--font-size-sm); }
.audit-event-detail-page__project-links { display: grid; gap: var(--spacing-xs); }
</style>
