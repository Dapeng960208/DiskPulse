<script setup>
import {
  ElButton,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElTableColumn,
  ElTag,
  ElTooltip,
} from 'element-plus';
import { computed, reactive, ref, watch } from 'vue';
import FilterForm from '@/components/form/QueryForm.vue';
import TimeRangePicker from '@/components/form/TimeRangePicker.vue';
import PieCharts from '@/common/charts/PieCharts.vue';
import LoadingCharts from '@/common/charts/LoadingCharts.vue';
import DataTable from '@/components/data/DataTable.vue';
import TableActionButton from '@/components/basic/TableActionButton.vue';
import storageClusterApi from '@/api/storage-cluster-api';
import { useClusterExport } from '@/composables/useClusterExport';
import { toUtcRange } from '@/utils/datetime.js';

const props = defineProps({
  clusterId: { type: Number, required: true },
  dateRange: { type: Array, required: true },
  active: { type: Boolean, default: true },
});

const emit = defineEmits(['update:dateRange', 'openSystemEventDetail']);

const localDateRange = computed({
  get: () => props.dateRange,
  set: (value) => emit('update:dateRange', value),
});

const severity = ref({ counts: {}, total: 0, sources: {} });
const faults = ref({ data: [] });
const systemEvents = ref({ data: [] });
const loading = ref(false);
const loadingSystemEvents = ref(false);
const loadedRangeKey = ref('');
const systemEventFilters = reactive({ keyword: '', severity: '' });
const systemEventPagination = reactive({ page: 1, pageSize: 20, total: 0 });

function rangeKey() {
  return props.dateRange.join('|');
}

const faultData = computed(() => faults.value?.data || []);
const systemEventData = computed(() => systemEvents.value?.data || []);
const severityChartData = computed(() => [
  ['严重', Number(severity.value?.counts?.critical) || 0],
  ['错误', Number(severity.value?.counts?.error) || 0],
  ['警告', Number(severity.value?.counts?.warning) || 0],
  ['信息', Number(severity.value?.counts?.info) || 0],
].filter(([, count]) => count > 0));

function hasReviewedVendorSemantics(event) {
  return event?.review_status === 'reviewed'
    && Boolean(event?.association_type)
    && event.association_type !== 'unknown';
}

function vendorEventTitle(event) {
  if (!hasReviewedVendorSemantics(event)) return '待审核 · 未分类厂商事件';
  return event.title_zh || '未收录的厂商事件代码';
}

function vendorEventAssociationLabel(event) {
  if (!hasReviewedVendorSemantics(event)) return '未分类厂商事件';
  return event.association_type_label || '未分类厂商事件';
}

function vendorEventAssociationTagType(event) {
  if (!hasReviewedVendorSemantics(event)) return 'info';
  if (event.association_type === 'fault_log') return 'danger';
  if (event.association_type === 'performance_anomaly') return 'warning';
  return 'info';
}

function vendorEventDescription(event) {
  if (!hasReviewedVendorSemantics(event)) {
    return '该事件代码尚未完成审核，不能根据候选定义推断系统问题；请结合规范化日志和厂商文档核查。';
  }
  return event.description_zh || '该代码尚未维护中文说明，请结合规范化日志核查。';
}

function vendorEventRecommendedSolution(event) {
  if (!hasReviewedVendorSemantics(event)) return '暂无可核验官方方案';
  return event.recommended_solution_zh || '暂无可核验官方方案';
}

function systemEventQueryParams() {
  const [start_time, end_time] = toUtcRange(localDateRange.value);
  return {
    start_time,
    end_time,
    ...(systemEventFilters.keyword.trim() ? { keyword: systemEventFilters.keyword.trim() } : {}),
    ...(systemEventFilters.severity ? { severity: systemEventFilters.severity } : {}),
    page: systemEventPagination.page,
    page_size: systemEventPagination.pageSize,
  };
}

function applySystemEventResponse(response) {
  systemEvents.value = response || { data: [] };
  systemEventPagination.total = Number(response?.total) || 0;
  systemEventPagination.page = Number(response?.page) || systemEventPagination.page;
  systemEventPagination.pageSize = Number(response?.page_size) || systemEventPagination.pageSize;
}

async function load() {
  if (!props.clusterId) return;
  loading.value = true;
  const [start_time, end_time] = toUtcRange(localDateRange.value);
  try {
    const [severityResponse, faultResponse, eventResponse] = await Promise.all([
      storageClusterApi.fetchErrorSeverity(props.clusterId, {
        start_time,
        end_time,
      }),
      storageClusterApi.fetchRepeatedFaults(props.clusterId, {
        start_time,
        end_time,
      }),
      storageClusterApi.fetchSystemEvents(props.clusterId, systemEventQueryParams()),
    ]);
    severity.value = severityResponse;
    faults.value = faultResponse;
    applySystemEventResponse(eventResponse);
    loadedRangeKey.value = rangeKey();
  } catch {
    severity.value = { counts: {}, total: 0, sources: {} };
    faults.value = { data: [] };
    systemEvents.value = { data: [] };
    systemEventPagination.total = 0;
    ElMessage.error('加载故障数据失败，请稍后重试');
  } finally {
    loading.value = false;
  }
}

async function loadSystemEvents(resetPage = false) {
  if (!props.clusterId) return;
  if (resetPage) systemEventPagination.page = 1;
  loadingSystemEvents.value = true;
  try {
    applySystemEventResponse(
      await storageClusterApi.fetchSystemEvents(props.clusterId, systemEventQueryParams()),
    );
  } catch {
    systemEvents.value = { data: [] };
    systemEventPagination.total = 0;
    ElMessage.error('加载系统事件失败，请稍后重试');
  } finally {
    loadingSystemEvents.value = false;
  }
}

function openSystemEventDetail(row) {
  emit('openSystemEventDetail', row);
}

function resetSystemEventFilters() {
  systemEventFilters.keyword = '';
  systemEventFilters.severity = '';
  loadSystemEvents(true);
}

function updateSystemEventPagination(pagination) {
  const pageSizeChanged = pagination.pageSize !== systemEventPagination.pageSize;
  systemEventPagination.pageSize = pagination.pageSize;
  systemEventPagination.page = pageSizeChanged ? 1 : pagination.page;
  loadSystemEvents();
}

function search() {
  systemEventPagination.page = 1;
  load();
}

function reset() {
  emit('update:dateRange', props.dateRange);
  load();
}

const { handleExport } = useClusterExport({
  clusterId: computed(() => props.clusterId),
  dateRange: localDateRange,
  defaultSection: 'faults',
});

watch(() => props.clusterId, load, { immediate: true });
watch(() => props.dateRange, () => {
  if (props.active) load();
});
watch(() => props.active, (active) => {
  if (active && loadedRangeKey.value !== rangeKey()) load();
});
</script>

<template>
  <section class="cluster-faults-tab">
    <FilterForm
      class="faults-filter"
      @query="search"
      @reset="reset">
      <ElFormItem
        label="时间范围"
        class="analytics-date-range query-form-field--date-range">
        <!-- Keep every time-based analytics tab on the backend range contract. -->
        <TimeRangePicker
          v-model="localDateRange"
          :max-days="180" />
      </ElFormItem>
      <template #actions>
        <ElDropdown @command="handleExport">
          <ElButton type="primary">导出报告</ElButton>
          <template #dropdown>
            <ElDropdownMenu>
              <ElDropdownItem command="severity:csv">错误级别 CSV</ElDropdownItem>
              <ElDropdownItem command="severity:excel">错误级别 Excel</ElDropdownItem>
              <ElDropdownItem command="severity:pdf">错误级别 PDF</ElDropdownItem>
              <ElDropdownItem command="faults:csv">重复故障 CSV</ElDropdownItem>
              <ElDropdownItem command="faults:excel">重复故障 Excel</ElDropdownItem>
              <ElDropdownItem command="faults:pdf">重复故障 PDF</ElDropdownItem>
              <ElDropdownItem
                divided
                command="all:csv">完整报告 CSV</ElDropdownItem>
              <ElDropdownItem command="all:excel">完整报告 Excel</ElDropdownItem>
              <ElDropdownItem command="all:pdf">完整报告 PDF</ElDropdownItem>
            </ElDropdownMenu>
          </template>
        </ElDropdown>
      </template>
    </FilterForm>
    <LoadingCharts
      v-if="loading"
      width="100%"
      height="360px" />
    <div v-else>
      <div
        v-if="!severity.total && !faultData.length"
        class="fault-analysis-empty">当前时间范围内暂无故障数据；如设备已有告警，请检查厂商事件采集权限</div>
      <div
        v-else
        class="fault-grid">
        <PieCharts
          :data="severityChartData"
          title="错误严重级别"
          width="100%"
          height="360px" />
        <DataTable :data="faultData">
          <ElTableColumn
            label="来源"
            class-name="mobile-hidden tablet-hidden"
            label-class-name="mobile-hidden tablet-hidden"
            prop="source" />
          <ElTableColumn
            label="事件代码与含义"
            min-width="260"
            show-overflow-tooltip>
            <template #default="{ row }">
              <strong>{{ row.title_zh || '未收录的厂商事件代码' }}</strong>
              <div class="text-secondary">{{ row.event_code || '-' }}</div>
            </template>
          </ElTableColumn>
          <ElTableColumn
            label="关联类型"
            min-width="130">
            <template #default="{ row }">
              <ElTag :type="row.association_type === 'fault_log' ? 'danger' : 'warning'">
                {{ row.association_type_label || '未分类厂商事件' }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn
            label="日志摘要"
            class-name="mobile-hidden tablet-hidden"
            label-class-name="mobile-hidden tablet-hidden"
            prop="log_excerpt"
            min-width="260"
            show-overflow-tooltip />
          <ElTableColumn
            label="次数"
            prop="count" />
          <ElTableColumn
            label="首次发生"
            class-name="mobile-hidden tablet-hidden"
            label-class-name="mobile-hidden tablet-hidden"
            prop="first_occurred_at" />
          <ElTableColumn
            label="最近发生"
            prop="last_occurred_at" />
          <ElTableColumn
            label="操作"
            align="right"
            fixed="right"
            width="110">
            <template #default="{ row }">
              <div class="list-row-actions">
                <TableActionButton
                  :data-testid="`repeated-event-log-${row.sample_event_id}`"
                  action="detail"
                  @click="openSystemEventDetail(row)">查看日志</TableActionButton>
              </div>
            </template>
          </ElTableColumn>
        </DataTable>
      </div>
      <div class="system-events">
        <h3>系统事件</h3>
        <FilterForm
          class="system-event-filter"
          @query="loadSystemEvents(true)"
          @reset="resetSystemEventFilters">
          <ElFormItem label="关键字">
            <ElInput
              v-model="systemEventFilters.keyword"
              clearable
              placeholder="事件代码、对象或内容" />
          </ElFormItem>
          <ElFormItem label="日志等级">
            <ElSelect
              v-model="systemEventFilters.severity"
              clearable
              placeholder="全部等级">
              <ElOption
                label="严重"
                value="critical" />
              <ElOption
                label="错误"
                value="error" />
              <ElOption
                label="警告"
                value="warning" />
              <ElOption
                label="信息"
                value="info" />
            </ElSelect>
          </ElFormItem>
        </FilterForm>
        <DataTable
          :data="systemEventData"
          :loading="loadingSystemEvents"
          :pagination="{
            ...systemEventPagination,
            pageSizes: [20, 50, 100],
            hideOnSinglePage: true,
            showJumper: true,
          }"
          @update:pagination="updateSystemEventPagination">
          <ElTableColumn
            label="来源"
            class-name="mobile-hidden tablet-hidden"
            label-class-name="mobile-hidden tablet-hidden"
            min-width="50"
            prop="source" />
          <ElTableColumn
            label="级别"
            min-width="50"
            prop="severity" />
          <ElTableColumn
            label="事件代码与含义"
            min-width="100"
            show-overflow-tooltip>
            <template #default="{ row }">
              <strong>{{ vendorEventTitle(row) }}</strong>
              <div class="text-secondary">{{ row.event_code || '-' }}</div>
            </template>
          </ElTableColumn>
          <ElTableColumn
            label="关联类型"
            min-width="50">
            <template #default="{ row }">
              <ElTooltip
                placement="top"
                effect="light"
                popper-class="system-event-association-tooltip">
                <template #content>
                  <div class="system-event-association-guidance">
                    <strong>关联提示</strong>
                    <p>{{ vendorEventDescription(row) }}</p>
                    <strong>采取措施</strong>
                    <p>{{ vendorEventRecommendedSolution(row) }}</p>
                  </div>
                </template>
                <ElTag :type="vendorEventAssociationTagType(row)">
                  {{ vendorEventAssociationLabel(row) }}
                </ElTag>
              </ElTooltip>
            </template>
          </ElTableColumn>
          <ElTableColumn
            label="事件对象"
            class-name="mobile-hidden tablet-hidden"
            label-class-name="mobile-hidden tablet-hidden"
            min-width="50"
            prop="object_name">
            <template #default="{ row }">
              <span :title="row.object_id && row.object_id !== row.object_name ? `原始标识：${row.object_id}` : undefined">
                {{ row.object_name || row.object_id || '-' }}
              </span>
            </template>
          </ElTableColumn>
          <ElTableColumn
            label="内容"
            class-name="mobile-hidden tablet-hidden"
            label-class-name="mobile-hidden tablet-hidden"
            min-width="300"
            prop="description"
            show-overflow-tooltip />
          <ElTableColumn
            label="发生时间"
            min-width="50"
            prop="occurred_at" />
          <ElTableColumn
            label="操作"
            align="right"
            fixed="right"
            width="110">
            <template #default="{ row }">
              <div class="list-row-actions">
                <TableActionButton
                  action="detail"
                  @click="openSystemEventDetail(row)">查看日志</TableActionButton>
              </div>
            </template>
          </ElTableColumn>
        </DataTable>
      </div>
    </div>
  </section>
</template>

<style scoped>
.cluster-faults-tab {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.faults-filter {
  margin-bottom: var(--spacing-md);
}

.faults-filter :deep(.analytics-date-range .el-date-editor) {
  width: 100%;
}

.fault-analysis-empty {
  padding: var(--spacing-xl) 0;
  color: var(--el-text-color-secondary);
  text-align: center;
}

.fault-grid {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(0, 2fr);
  gap: 16px;
}

.system-events {
  margin-top: 20px;
}

.system-event-filter {
  margin-bottom: var(--spacing-md);
}

.system-event-association-guidance {
  max-width: 360px;
  line-height: 1.5;
}

.system-event-association-guidance p {
  margin: var(--spacing-xs) 0 var(--spacing-sm);
}

.system-event-association-guidance p:last-child {
  margin-bottom: 0;
}

@media (max-width: 960px) {
  .fault-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
