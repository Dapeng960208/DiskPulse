<script setup>
import { computed, ref, watch } from 'vue';
import { ElDescriptions, ElDescriptionsItem, ElDrawer, ElEmpty, ElTag } from 'element-plus';
import auditEventsApi from '@/api/audit-events-api.js';

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
  return event.actor?.common_name || event.actor?.commonName || event.actor?.rd_username || event.actor?.username || event.actor_user_id || '-';
}

function resourceName(event) {
  const identity = event.resource_name || event.resource_type || '-';
  return event.resource_id == null ? identity : `${identity} #${event.resource_id}`;
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
      <ElDescriptionsItem label="项目">{{ current.project?.name || current.project_id || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem label="资源">{{ resourceName(current) }}</ElDescriptionsItem>
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
</style>
