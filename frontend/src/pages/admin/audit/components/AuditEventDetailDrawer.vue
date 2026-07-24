<script setup>
import { computed, ref, watch } from 'vue';
import { ElButton, ElDescriptions, ElDescriptionsItem, ElDrawer, ElEmpty, ElTag } from 'element-plus';
import auditEventsApi from '@/api/audit-events-api.js';
import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';
import {
  auditActionDescription,
  auditActorTypeLabel,
  auditOutcomeLabel,
  auditPhaseLabel,
  auditRequesterLabel,
  auditSummaryEntries,
  formatAuditOccurredAt,
  hasAuditValue,
} from '@/utils/audit-event-display.js';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  event: { type: Object, default: null },
});
const emit = defineEmits(['update:modelValue', 'analyze']);
const detail = ref(null);
const loading = ref(false);
const error = ref('');

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});
const current = computed(() => detail.value || props.event || {});
const title = computed(() => current.value.id ? `审计事件 #${current.value.id}` : '审计事件详情');

function summary(value) {
  if (value == null || value === '') return '-';
  return typeof value === 'string' ? value : JSON.stringify(value, null, 2);
}

function outcomeType(outcome) {
  return { success: 'success', denied: 'warning', failure: 'danger' }[outcome] || 'info';
}

function resourceName(event) {
  const resource = event.resource;
  const resourceType = resource?.type || event.resource_type;
  const typeLabel = resourceTypeLabel(resourceType);
  if (resource?.name) return `${typeLabel} · ${resource.name}`;
  return event.resource_id == null ? typeLabel : `${typeLabel} #${event.resource_id}`;
}

function resourceTypeLabel(resourceType) {
  return {
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
}

function resourceRoute(event) {
  const resource = event.resource || { type: event.resource_type, id: event.resource_id };
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

async function load() {
  if (!props.event?.id || !visible.value) return;
  loading.value = true;
  error.value = '';
  detail.value = null;
  try {
    detail.value = await auditEventsApi.fetchById(props.event.id);
  } catch {
    error.value = '加载审计详情失败，当前仅展示列表摘要。';
  } finally {
    loading.value = false;
  }
}

function analyzeCurrentEvent() {
  if (current.value.id) emit('analyze', current.value);
}

watch(() => [props.event?.id, visible.value], load, { immediate: true });
</script>

<template>
  <ElDrawer
    v-model="visible"
    :title="title"
    direction="rtl"
    size="680px">
    <ElDescriptions
      v-if="current.id"
      v-loading="loading"
      :column="1"
      border>
      <ElDescriptionsItem label="发生时间">{{ formatAuditOccurredAt(current.occurred_at || current.created_at) }}</ElDescriptionsItem>
      <ElDescriptionsItem label="结果"><ElTag :type="outcomeType(current.outcome)">{{ auditOutcomeLabel(current.outcome || current.result) }}</ElTag></ElDescriptionsItem>
      <ElDescriptionsItem label="操作">{{ auditActionDescription(current.action) }}</ElDescriptionsItem>
      <ElDescriptionsItem label="记录阶段">{{ auditPhaseLabel(current.phase) }}</ElDescriptionsItem>
      <ElDescriptionsItem label="请求/触发方">{{ auditRequesterLabel(current) }}</ElDescriptionsItem>
      <ElDescriptionsItem label="执行来源">{{ auditActorTypeLabel(current.actor_type) }}</ElDescriptionsItem>
      <ElDescriptionsItem label="项目">
        <AccessibleResourceLink
          v-if="current.project?.id"
          :to="{ name: 'ProjectDetail', params: { id: current.project.id } }">{{ current.project.name }}</AccessibleResourceLink>
        <span v-else>无直接项目</span>
      </ElDescriptionsItem>
      <ElDescriptionsItem label="资源"><AccessibleResourceLink :to="resourceRoute(current)">{{ resourceName(current) }}</AccessibleResourceLink></ElDescriptionsItem>
      <ElDescriptionsItem label="关联项目">
        <div
          v-if="current.related_projects?.length"
          class="audit-event-detail-drawer__project-links">
          <AccessibleResourceLink
            v-for="project in current.related_projects"
            :key="project.id"
            :to="{ name: 'ProjectDetail', params: { id: project.id } }">{{ project.name }}</AccessibleResourceLink>
        </div>
        <span v-else>无项目关联</span>
      </ElDescriptionsItem>
      <ElDescriptionsItem
        v-if="current.relation_path"
        label="关联路径">{{ current.relation_path }}</ElDescriptionsItem>
      <ElDescriptionsItem
        v-if="current.trace_id"
        label="Trace ID">{{ current.trace_id }}</ElDescriptionsItem>
      <ElDescriptionsItem
        v-if="current.request_id"
        label="请求 ID">{{ current.request_id }}</ElDescriptionsItem>
      <ElDescriptionsItem
        v-if="current.reason_code"
        label="原因码">{{ current.reason_code }}</ElDescriptionsItem>
      <ElDescriptionsItem
        v-if="hasAuditValue(current.before_summary)"
        label="变更前摘要">
        <dl
          v-if="auditSummaryEntries(current.before_summary).length"
          class="audit-event-detail-drawer__summary">
          <template
            v-for="entry in auditSummaryEntries(current.before_summary)"
            :key="entry.label">
            <dt>{{ entry.label }}</dt><dd>{{ entry.value }}</dd>
          </template>
        </dl>
        <pre v-else>{{ summary(current.before_summary) }}</pre>
      </ElDescriptionsItem>
      <ElDescriptionsItem
        v-if="hasAuditValue(current.after_summary)"
        :label="current.action === 'storage.collection.run' ? '采集结果' : '变更后摘要'">
        <dl
          v-if="auditSummaryEntries(current.after_summary).length"
          class="audit-event-detail-drawer__summary">
          <template
            v-for="entry in auditSummaryEntries(current.after_summary)"
            :key="entry.label">
            <dt>{{ entry.label }}</dt><dd>{{ entry.value }}</dd>
          </template>
        </dl>
        <pre v-else>{{ summary(current.after_summary) }}</pre>
      </ElDescriptionsItem>
      <ElDescriptionsItem
        v-if="hasAuditValue(current.metadata)"
        label="附加元数据">
        <dl
          v-if="auditSummaryEntries(current.metadata).length"
          class="audit-event-detail-drawer__summary">
          <template
            v-for="entry in auditSummaryEntries(current.metadata)"
            :key="entry.label">
            <dt>{{ entry.label }}</dt><dd>{{ entry.value }}</dd>
          </template>
        </dl>
        <pre v-else>{{ summary(current.metadata) }}</pre>
      </ElDescriptionsItem>
    </ElDescriptions>
    <ElEmpty
      v-else-if="!loading"
      description="未找到审计事件" />
    <p
      v-if="error"
      class="audit-event-detail-drawer__error">{{ error }}</p>
    <template #footer>
      <ElButton
        :disabled="!current.id"
        type="primary"
        @click="analyzeCurrentEvent">AI 研判</ElButton>
    </template>
  </ElDrawer>
</template>

<style scoped>
pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: var(--font-size-sm); }
.audit-event-detail-drawer__error { margin: var(--spacing-md) 0 0; color: var(--color-danger); }
.audit-event-detail-drawer__project-links { display: grid; gap: var(--spacing-xs); }
.audit-event-detail-drawer__summary { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: var(--spacing-xs) var(--spacing-md); margin: 0; }
.audit-event-detail-drawer__summary dt { color: var(--text-secondary); }
.audit-event-detail-drawer__summary dd { margin: 0; text-align: right; }
</style>
