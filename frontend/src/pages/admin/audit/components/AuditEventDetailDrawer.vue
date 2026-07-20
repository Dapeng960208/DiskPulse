<script setup>
import { computed, ref, watch } from 'vue';
import { ElDescriptions, ElDescriptionsItem, ElDrawer, ElEmpty, ElTag } from 'element-plus';
import auditEventsApi from '@/api/audit-events-api.js';
import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  event: { type: Object, default: null },
});
const emit = defineEmits(['update:modelValue']);
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

function actorName(event) {
  return event.actor?.display_name || event.actor?.common_name || event.actor?.commonName || event.actor?.rd_username || event.actor?.username || event.actor_user_id || '-';
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
      <ElDescriptionsItem label="发生时间">{{ current.occurred_at || current.created_at || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="结果"><ElTag :type="outcomeType(current.outcome)">{{ current.outcome || current.result || '-' }}</ElTag></ElDescriptionsItem>
      <ElDescriptionsItem label="操作">{{ current.action || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="主体">{{ actorName(current) }}</ElDescriptionsItem>
      <ElDescriptionsItem label="项目">
        <AccessibleResourceLink :to="{ name: 'ProjectDetail', params: { id: current.project?.id } }">{{ current.project?.name || current.project_id || '-' }}</AccessibleResourceLink>
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
      <ElDescriptionsItem label="关联路径">{{ current.relation_path || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="资源路径">{{ current.resource_path || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="Trace ID">{{ current.trace_id || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="请求 ID">{{ current.request_id || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="原因码">{{ current.reason_code || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="客户端 IP">{{ current.metadata?.client_ip || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="请求地址">{{ current.metadata?.endpoint || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="变更前摘要"><pre>{{ summary(current.before_summary) }}</pre></ElDescriptionsItem>
      <ElDescriptionsItem label="变更后摘要"><pre>{{ summary(current.after_summary) }}</pre></ElDescriptionsItem>
      <ElDescriptionsItem label="附加元数据"><pre>{{ summary(current.metadata) }}</pre></ElDescriptionsItem>
    </ElDescriptions>
    <ElEmpty
      v-else-if="!loading"
      description="未找到审计事件" />
    <p
      v-if="error"
      class="audit-event-detail-drawer__error">{{ error }}</p>
  </ElDrawer>
</template>

<style scoped>
pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: var(--font-size-sm); }
.audit-event-detail-drawer__error { margin: var(--spacing-md) 0 0; color: var(--color-danger); }
.audit-event-detail-drawer__project-links { display: grid; gap: var(--spacing-xs); }
</style>
