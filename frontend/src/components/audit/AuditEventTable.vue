<script setup>
import { ElButton, ElTableColumn, ElTag } from 'element-plus';
import DataTable from '@/components/data/DataTable.vue';

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

function actorLabel(row) {
  return row.actor?.rd_username || row.actor?.username || row.actor_user_id || '-';
}

function resourceLabel(row) {
  if (!row.resource_type) return '-';
  return row.resource_id == null ? row.resource_type : `${row.resource_type} #${row.resource_id}`;
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
      prop="occurred_at"
      label="时间"
      min-width="176" />
    <ElTableColumn
      label="主体"
      min-width="130">
      <template #default="{ row }">{{ actorLabel(row) }}</template>
    </ElTableColumn>
    <ElTableColumn
      prop="action"
      label="操作"
      min-width="180"
      show-overflow-tooltip />
    <ElTableColumn
      label="资源"
      min-width="170">
      <template #default="{ row }">{{ resourceLabel(row) }}</template>
    </ElTableColumn>
    <ElTableColumn
      v-if="showProject"
      label="项目"
      min-width="130">
      <template #default="{ row }">{{ row.project?.name || row.project_id || '-' }}</template>
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
        <ElButton
          size="small"
          plain
          @click="emit('show-detail', row)">详情</ElButton>
      </template>
    </ElTableColumn>
  </DataTable>
</template>
