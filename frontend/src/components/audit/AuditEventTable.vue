<script setup>
import { ElButton, ElTableColumn, ElTag } from 'element-plus';
import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';
import DataTable from '@/components/data/DataTable.vue';
import TableActionButton from '@/components/basic/TableActionButton.vue';
import { auditActionLabel, auditRequesterLabel, formatAuditOccurredAt } from '@/utils/audit-event-display.js';

defineProps({
  events: {
    type: Array,
    default: () => [],
  },
  loading: Boolean,
  error: {
    type: String,
    default: '',
  },
  pagination: Object,
  showProject: {
    type: Boolean,
    default: true,
  },
  showDetails: Boolean,
});

const emit = defineEmits(['update:pagination', 'show-detail']);

function resourceLabel(row) {
  const resource = row.resource;
  const resourceType = resource?.type || row.resource_type;
  const typeLabel = resourceTypeLabel(resourceType);
  if (resource?.name) return `${typeLabel} · ${resource.name}`;
  if (!resourceType) return '-';
  return row.resource_id == null ? typeLabel : `${typeLabel} #${row.resource_id}`;
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

function resourceRoute(row) {
  const resource = row.resource || { type: row.resource_type, id: row.resource_id };
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

function relatedProjects(row) {
  return row.related_projects || [];
}

function outcomeType(outcome) {
  return { success: 'success', denied: 'warning', failure: 'danger' }[outcome] || 'info';
}
</script>

<template>
  <DataTable
    density="compact"
    :data="events"
    :loading="loading"
    :error="error"
    :pagination="pagination"
    @update:pagination="emit('update:pagination', $event)">
    <ElTableColumn
      label="时间"
      min-width="176">
      <template #default="{ row }"><time :datetime="row.occurred_at">{{ formatAuditOccurredAt(row.occurred_at) }}</time></template>
    </ElTableColumn>
    <ElTableColumn
      label="主体"
      min-width="130">
      <template #default="{ row }">{{ auditRequesterLabel(row) }}</template>
    </ElTableColumn>
    <ElTableColumn
      label="操作"
      min-width="180"
      show-overflow-tooltip>
      <template #default="{ row }"><span :title="row.action">{{ auditActionLabel(row.action) }}</span></template>
    </ElTableColumn>
    <ElTableColumn
      label="资源"
      min-width="210"
      show-overflow-tooltip>
      <template #default="{ row }">
        <AccessibleResourceLink :to="resourceRoute(row)">{{ resourceLabel(row) }}</AccessibleResourceLink>
      </template>
    </ElTableColumn>
    <ElTableColumn
      v-if="showProject"
      label="关联项目"
      min-width="220">
      <template #default="{ row }">
        <div
          v-if="row.project || relatedProjects(row).length"
          class="audit-event-table__project-links">
          <div v-if="row.project">
            <span class="audit-event-table__relation-kind">直接</span>
            <AccessibleResourceLink :to="{ name: 'ProjectDetail', params: { id: row.project.id } }">{{ row.project.name }}</AccessibleResourceLink>
          </div>
          <div
            v-for="project in relatedProjects(row)"
            :key="project.id">
            <span class="audit-event-table__relation-kind">经资源</span>
            <AccessibleResourceLink :to="{ name: 'ProjectDetail', params: { id: project.id } }">{{ project.name }}</AccessibleResourceLink>
          </div>
          <p
            v-if="row.relation_path"
            class="audit-event-table__relation-path">{{ row.relation_path }}</p>
        </div>
        <span v-else>无项目关联</span>
      </template>
    </ElTableColumn>
    <ElTableColumn
      label="结果"
      width="104">
      <template #default="{ row }"><ElTag :type="outcomeType(row.outcome)">{{ row.outcome || '-' }}</ElTag></template>
    </ElTableColumn>
    <ElTableColumn
      prop="trace_id"
      label="Trace ID"
      min-width="180"
      show-overflow-tooltip />
    <ElTableColumn
      v-if="showDetails"
      align="right"
      width="88"
      fixed="right">
      <template #default="{ row }">
        <TableActionButton
          action="detail"
          @click="emit('show-detail', row)">详情</TableActionButton>
      </template>
    </ElTableColumn>
  </DataTable>
</template>

<style scoped>
.audit-event-table__project-links { display: grid; gap: var(--spacing-xs); }
.audit-event-table__relation-kind { margin-right: var(--spacing-xs); color: var(--text-tertiary); font-size: var(--font-size-xs); }
.audit-event-table__relation-path { margin: 0; color: var(--text-tertiary); font-size: var(--font-size-xs); line-height: var(--line-height-tight); }
</style>
