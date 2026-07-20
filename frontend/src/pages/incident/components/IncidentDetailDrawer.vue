<script setup>
import { computed, reactive, ref, watch } from 'vue';
import {
  ElButton,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElDrawer,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElTag,
  ElTooltip,
} from 'element-plus';
import incidentApi from '@/api/incident-api.js';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  incident: { type: Object, default: null },
});
const emit = defineEmits(['update:modelValue', 'updated']);

const detail = ref(null);
const loading = ref(false);
const error = ref('');
const comment = ref('');
const activeAction = ref('');
const maintenanceVisible = ref(false);
const maintenanceForm = reactive({
  starts_at: null,
  ends_at: null,
  reason: '',
});

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});
const current = computed(() => detail.value || props.incident || {});
const capabilities = computed(() => current.value.capabilities || {});
const canClaim = computed(() => capabilities.value.claim
  ?? (capabilities.value.edit === true && current.value.assigned_user_id == null));
const canRelease = computed(() => capabilities.value.release
  ?? (capabilities.value.edit === true && current.value.assigned_user_id != null));
const nextStatus = computed(() => ({
  open: 'acknowledged',
  acknowledged: 'investigating',
  investigating: 'mitigated',
  mitigated: 'resolved',
})[current.value.status] || null);
const isUpdating = computed(() => Boolean(activeAction.value));

function formatLocalDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  const pad = (part) => String(part).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

const categoryLabels = {
  capacity_pressure: '容量压力',
  device_fault: '设备健康风险',
  performance_contention: '性能争用',
  telemetry_blindspot: '监控盲区',
};
const categoryDescriptions = {
  capacity_pressure: '容量预测显示可能耗尽，或当前资源的有效告警规则达到阈值。默认按硬限额 80%/90%/95%；用户目录优先采用项目组规则，其次项目规则，最后系统规则。',
  device_fault: 'NetApp EMS 或 PowerScale（Isilon）厂商系统事件达到严重级别、同一故障指纹反复出现，或同一时段采集异常时创建。它表示待核查的设备健康风险，不等同于已确认硬件损坏。',
  performance_contention: '同一指标连续三个相邻 5 分钟桶偏离 28 天同星期同小时基线，且鲁棒 Z 分数绝对值均不低于 3.5。',
  telemetry_blindspot: '监控盲区：容量、厂商事件或性能监控采集过期、采集失败或覆盖率不足，当前数据不足以可靠判断资产状态。',
};
const confidenceLabels = {
  high: '高',
  medium: '中',
  low: '低',
  insufficient: '证据不足',
};
const confidenceDescriptions = {
  high: '有多类相互独立的最新证据支持，建议优先处理。',
  medium: '已有支持证据，但仍需回查原始事件或监控数据。',
  low: '证据较少或存在冲突，只能作为排查线索。',
  insufficient: '当前证据不足，不能给出可靠的排查方向。',
};
const evidenceSourceLabels = {
  forecast: '容量预测',
  storage_alert: 'DiskPulse 存储告警',
  vendor_event: '厂商系统事件',
  telemetry: '监控采集',
  telemetry_quality: '监控数据质量',
};
const evidenceTypeLabels = {
  forecast_exhaustion: '预测容量可能耗尽',
  hard_limit_alert: '硬限额告警',
  soft_limit_alert: '软限额告警',
  severe_vendor_event: '厂商严重系统事件',
  repeated_fault: '重复故障事件',
  collection_error: '采集异常',
  telemetry_stale: '采集已过期',
  coverage_insufficient: '覆盖不足',
};
const timelineLabels = {
  created: '系统创建事件',
  opened: '事件创建',
  evidence_added: '新增证据',
  claimed: '已认领',
  released: '已释放',
  status_changed: '状态已推进',
  severity_changed: '风险级别已调整',
  silenced: '已静默通知',
  unsilenced: '已恢复通知',
  commented: '添加评论',
};
const statusLabels = {
  open: '未处理',
  acknowledged: '已确认',
  investigating: '调查中',
  mitigated: '已缓解',
  resolved: '已解决',
};
const statusDescriptions = {
  open: '系统已创建事件，尚未确认由谁处理。',
  acknowledged: '已确认收到事件，下一步应开始分析。',
  investigating: '正在核对原始告警、厂商事件、预测和监控数据。',
  mitigated: '影响已缓解，仍需观察是否出现新证据。',
  resolved: '处理完成；若 24 小时内出现同类新证据，系统会重新打开事件。',
};
const nextStatusTooltip = computed(() => nextStatus.value
  ? `仅允许相邻推进至“${statusLabels[nextStatus.value]}”，${statusDescriptions[nextStatus.value]}`
  : '事件已解决，不能继续推进状态。');

function evidencePresentation(evidence) {
  if (evidence.presentation) return evidence.presentation;
  const sourceLabel = evidenceSourceLabels[evidence.source] || '关联记录';
  const title = evidenceTypeLabels[evidence.evidence_type] || '关联事件证据';
  return {
    group_key: evidence.source || evidence.evidence_type || 'other',
    group_label: sourceLabel,
    title,
    summary: `系统关联了${title}，请结合原始记录核查。`,
    scope_label: sourceLabel,
    technical_ref: evidence.source_ref || '-',
  };
}

const evidenceGroups = computed(() => {
  const groups = new Map();
  for (const evidence of current.value.evidence || []) {
    const presentation = evidencePresentation(evidence);
    const key = presentation.group_key || evidence.source || 'other';
    if (!groups.has(key)) {
      groups.set(key, { key, label: presentation.group_label || '关联依据', items: [] });
    }
    groups.get(key).items.push({ ...evidence, presentation });
  }
  return [...groups.values()];
});

function timelinePresentation(item) {
  if (item.presentation) return item.presentation;
  return {
    action_label: timelineLabels[item.event_type] || '事件更新',
    summary: item.comment || '系统记录了一次事件更新。',
    actor_label: item.actor_user_id == null ? '系统' : `用户 #${item.actor_user_id}`,
  };
}

async function load() {
  if (!props.incident?.id || !visible.value) return;
  loading.value = true;
  error.value = '';
  try {
    detail.value = await incidentApi.fetchIncident(props.incident.id);
  } catch {
    error.value = '加载事件详情失败，请稍后重试';
  } finally {
    loading.value = false;
  }
}

async function updateIncident(payload, action, successMessage) {
  if (!current.value.id) return;
  activeAction.value = action;
  error.value = '';
  try {
    await incidentApi.updateIncident(current.value.id, payload);
    await load();
    ElMessage.success(successMessage);
    emit('updated');
  } catch {
    error.value = '更新事件失败，请确认当前项目权限后重试';
    ElMessage.error(error.value);
  } finally {
    activeAction.value = '';
  }
}

async function submitComment() {
  const content = comment.value.trim();
  if (!content || !current.value.id) return;
  try {
    await incidentApi.createComment(current.value.id, { content });
    comment.value = '';
    await load();
    emit('updated');
  } catch {
    error.value = '提交评论失败，请稍后重试';
  }
}

function openMaintenance() {
  maintenanceForm.starts_at = new Date();
  maintenanceForm.ends_at = new Date(Date.now() + 60 * 60 * 1000);
  maintenanceForm.reason = '';
  maintenanceVisible.value = true;
}

async function submitMaintenance() {
  if (!current.value.project_id || !maintenanceForm.starts_at || !maintenanceForm.ends_at || !maintenanceForm.reason.trim()) return;
  try {
    await incidentApi.createMaintenanceWindow({
      project_id: current.value.project_id,
      storage_cluster_id: current.value.storage_cluster_id,
      asset_type: current.value.asset_type,
      asset_id: current.value.asset_id,
      starts_at: new Date(maintenanceForm.starts_at).toISOString(),
      ends_at: new Date(maintenanceForm.ends_at).toISOString(),
      reason: maintenanceForm.reason.trim(),
    });
    maintenanceVisible.value = false;
    ElMessage.success('维护窗口已创建');
  } catch {
    error.value = '创建维护窗口失败，请确认项目管理员权限后重试';
    ElMessage.error(error.value);
  }
}

watch(() => [props.incident?.id, props.modelValue], load, { immediate: true });
</script>

<template>
  <ElDrawer
    v-model="visible"
    size="min(720px, 100%)"
    :title="`事件 #${current.id || '-'}`">
    <p
      v-if="error"
      class="incident-detail__error">{{ error }}</p>
    <section
      v-if="current.id"
      v-loading="loading"
      class="incident-detail">
      <ElDescriptions
        :column="2"
        border>
        <ElDescriptionsItem label="受影响对象">{{ current.display_name }}</ElDescriptionsItem>
        <ElDescriptionsItem label="事件类型"><ElTooltip :content="categoryDescriptions[current.category] || '未知事件类型。'"><span>{{ categoryLabels[current.category] || current.category }}</span></ElTooltip></ElDescriptionsItem>
        <ElDescriptionsItem label="处置状态"><ElTooltip :content="statusDescriptions[current.status] || '未知处置状态。'"><span>{{ statusLabels[current.status] || current.status }}</span></ElTooltip></ElDescriptionsItem>
        <ElDescriptionsItem label="认领状态"><ElTag :type="current.assigned_user_id == null ? 'info' : 'success'">{{ current.assigned_user_id == null ? '待认领' : '已认领' }}</ElTag></ElDescriptionsItem>
        <ElDescriptionsItem label="风险级别"><ElTag :type="current.severity === 'critical' ? 'danger' : 'warning'">{{ current.severity === 'critical' ? '严重' : '警告' }}</ElTag></ElDescriptionsItem>
      </ElDescriptions>

      <div
        v-if="capabilities.edit"
        class="incident-detail__actions list-row-actions">
        <ElTooltip
          v-if="canClaim"
          content="将事件指派给当前登录用户，明确处理责任。"><ElButton
            data-testid="incident-claim"
            size="small"
            :loading="activeAction === 'claim'"
            :disabled="isUpdating"
            @click="updateIncident({ claim: true }, 'claim', '事件已认领')">认领</ElButton></ElTooltip>
        <ElTooltip
          v-if="canRelease"
          content="取消当前认领；仅认领人或超级管理员可以释放。"><ElButton
            data-testid="incident-release"
            size="small"
            :loading="activeAction === 'release'"
            :disabled="isUpdating"
            @click="updateIncident({ claim: false }, 'release', '事件已释放')">释放</ElButton></ElTooltip>
        <ElTooltip
          v-if="nextStatus"
          :content="nextStatusTooltip"><ElButton
            type="primary"
            size="small"
            :loading="activeAction === 'status'"
            :disabled="isUpdating"
            @click="updateIncident({ status: nextStatus }, 'status', `事件已推进为${statusLabels[nextStatus]}`)">推进为 {{ statusLabels[nextStatus] }}</ElButton></ElTooltip>
        <ElTooltip content="恢复派生事件的后续通知，不删除事件、证据或原始告警。"><ElButton
          size="small"
          :loading="activeAction === 'unsilence'"
          :disabled="isUpdating"
          @click="updateIncident({ silenced_until: null }, 'unsilence', '事件静默已取消')">取消静默</ElButton></ElTooltip>
      </div>
      <div
        v-if="capabilities.create_maintenance_window"
        class="incident-detail__actions">
        <ElTooltip content="在指定 UTC 时间段内抑制该资产的派生事件创建、重开和通知；采集、原始告警及厂商事件仍会保留。"><ElButton
          type="warning"
          plain
          size="small"
          @click="openMaintenance">创建维护窗口</ElButton></ElTooltip>
      </div>

      <section class="incident-detail__section">
        <ElTooltip content="由服务端按固定证据权重计算，不使用 AI 自由生成结论。"><h3>确定性诊断</h3></ElTooltip>
        <p class="incident-detail__hint">这是基于已记录证据生成的规则化排查建议，不是 AI 自由生成的故障结论。</p>
        <p v-if="!current.diagnosis">尚无足够证据生成诊断。</p>
        <template v-else>
          <p>建议可靠性：<ElTooltip content="高可靠性要求回放验证开关已启用、候选分数至少 0.8，且至少有两类独立证据。"><ElTag>{{ confidenceLabels[current.diagnosis.confidence] || current.diagnosis.confidence }}</ElTag></ElTooltip> {{ confidenceDescriptions[current.diagnosis.confidence] || '请结合证据引用进行核查。' }}</p>
          <ul class="incident-detail__candidate-list">
            <li
              v-for="candidate in current.diagnosis.candidates || []"
              :key="candidate.category">
              建议优先核查{{ categoryLabels[candidate.category] || candidate.category }}（证据匹配分 {{ candidate.score }}）
              <span>；依据 {{ (candidate.evidence_refs || []).join('、') || '无' }}</span>
              <span v-if="candidate.data_gaps?.length">；待补充 {{ candidate.data_gaps.join('、') }}</span>
            </li>
          </ul>
        </template>
      </section>

      <section class="incident-detail__section">
        <h3>关联概览</h3>
        <p v-if="evidenceGroups.length === 0">暂无关联证据。</p>
        <ul
          v-else
          class="incident-detail__evidence-overview"
          aria-label="关联证据概览">
          <li
            v-for="group in evidenceGroups"
            :key="group.key">
            <span>{{ group.label }}</span>
            <ElTag
              type="info"
              size="small">{{ group.items.length }} 项</ElTag>
          </li>
        </ul>
      </section>

      <section class="incident-detail__section">
        <h3>关联证据</h3>
        <p v-if="evidenceGroups.length === 0">暂无关联证据。</p>
        <ul
          v-else
          class="incident-detail__evidence-groups">
          <li
            v-for="group in evidenceGroups"
            :key="group.key">
            <h4>{{ group.label }}（{{ group.items.length }} 项）</h4>
            <article
              v-for="evidence in group.items"
              :key="evidence.id"
              class="incident-detail__evidence-item">
              <h5>{{ evidence.presentation.title }}</h5>
              <dl>
                <div><dt>异常说明</dt><dd>{{ evidence.presentation.summary }}</dd></div>
                <div><dt>影响范围</dt><dd>{{ current.display_name || '当前对象' }} · {{ evidence.presentation.scope_label }}</dd></div>
                <div><dt>发现时间</dt><dd>{{ formatLocalDateTime(evidence.observed_at) }}</dd></div>
              </dl>
              <details>
                <summary>技术信息</summary>
                <code>{{ evidence.presentation.technical_ref }}</code>
              </details>
            </article>
          </li>
        </ul>
      </section>

      <section class="incident-detail__section">
        <h3>时间线</h3>
        <p v-if="!(current.timeline || []).length">暂无操作记录。</p>
        <ol
          v-else
          class="incident-detail__timeline">
          <li
            v-for="item in current.timeline || []"
            :key="item.id">
            <time>{{ formatLocalDateTime(item.occurred_at) }}</time>
            <div>
              <strong>{{ timelinePresentation(item).action_label }}</strong>
              <p>{{ timelinePresentation(item).summary }}</p>
              <span>操作人：{{ timelinePresentation(item).actor_label }}</span>
            </div>
          </li>
        </ol>
      </section>

      <section
        v-if="capabilities.edit"
        class="incident-detail__section">
        <h3>添加评论</h3>
        <ElInput
          v-model="comment"
          type="textarea"
          :rows="3"
          maxlength="2000"
          show-word-limit
          placeholder="记录处理结论或后续动作" />
        <ElButton
          class="incident-detail__comment"
          type="primary"
          size="small"
          :disabled="!comment.trim()"
          @click="submitComment">提交评论</ElButton>
      </section>
    </section>
  </ElDrawer>

  <ElDialog
    v-model="maintenanceVisible"
    title="创建维护窗口"
    width="520px">
    <ElForm label-position="top">
      <ElFormItem label="开始时间（UTC）"><ElDatePicker
        v-model="maintenanceForm.starts_at"
        type="datetime" /></ElFormItem>
      <ElFormItem label="结束时间（UTC）"><ElDatePicker
        v-model="maintenanceForm.ends_at"
        type="datetime" /></ElFormItem>
      <ElFormItem label="原因"><ElInput
        v-model="maintenanceForm.reason"
        maxlength="500" /></ElFormItem>
    </ElForm>
    <template #footer><ElButton @click="maintenanceVisible = false">取消</ElButton><ElButton
      type="primary"
      @click="submitMaintenance">创建</ElButton></template>
  </ElDialog>
</template>

<style scoped>
.incident-detail { display: grid; gap: var(--spacing-md); }
.incident-detail__error { margin: 0 0 var(--spacing-md); color: var(--danger-color); }
.incident-detail__actions { display: flex; flex-wrap: wrap; gap: 8px; }
.incident-detail__section { display: grid; gap: 8px; }
.incident-detail__section h3 { margin: 0; font-size: var(--font-size-base); color: var(--text-primary); }
.incident-detail__section p { margin: 0; color: var(--text-secondary); }
.incident-detail__hint { padding: 8px 10px; border-left: 3px solid var(--primary-color); background: var(--bg-secondary); font-size: var(--font-size-sm); }
.incident-detail__candidate-list { margin: 0; padding-left: 20px; color: var(--text-primary); }
.incident-detail__candidate-list span { color: var(--text-secondary); }
.incident-detail__evidence-overview { display: flex; flex-wrap: wrap; gap: 8px; margin: 0; padding: 0; list-style: none; }
.incident-detail__evidence-overview li { display: inline-flex; align-items: center; gap: 6px; padding: 6px 8px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); color: var(--text-secondary); font-size: var(--font-size-sm); }
.incident-detail__evidence-groups { display: grid; gap: var(--spacing-sm); margin: 0; padding: 0; list-style: none; }
.incident-detail__evidence-groups > li { display: grid; gap: 8px; }
.incident-detail__evidence-groups h4, .incident-detail__evidence-item h5 { margin: 0; color: var(--text-primary); font-size: var(--font-size-sm); }
.incident-detail__evidence-item { display: grid; gap: 8px; padding: var(--spacing-sm); border: 1px solid var(--border-color); border-radius: var(--radius-sm); background: var(--bg-secondary); }
.incident-detail__evidence-item dl { display: grid; gap: 6px; margin: 0; }
.incident-detail__evidence-item dl div { display: grid; grid-template-columns: 76px minmax(0, 1fr); gap: 8px; }
.incident-detail__evidence-item dt { color: var(--text-secondary); font-size: var(--font-size-sm); }
.incident-detail__evidence-item dd { margin: 0; color: var(--text-primary); font-size: var(--font-size-sm); word-break: break-word; }
.incident-detail__evidence-item details { color: var(--text-secondary); font-size: var(--font-size-sm); }
.incident-detail__evidence-item code { display: block; margin-top: 6px; overflow-wrap: anywhere; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
.incident-detail__timeline { display: grid; gap: var(--spacing-sm); margin: 0; padding: 0; list-style: none; }
.incident-detail__timeline li { display: grid; grid-template-columns: 156px minmax(0, 1fr); gap: var(--spacing-sm); padding-bottom: var(--spacing-sm); border-bottom: 1px solid var(--border-color); }
.incident-detail__timeline li:last-child { padding-bottom: 0; border-bottom: 0; }
.incident-detail__timeline time, .incident-detail__timeline span { color: var(--text-secondary); font-size: var(--font-size-sm); }
.incident-detail__timeline p { margin: 4px 0; color: var(--text-primary); font-size: var(--font-size-sm); }
.incident-detail__comment { justify-self: end; }
@media (max-width: 640px) { .incident-detail__timeline li { grid-template-columns: 1fr; gap: 4px; } .incident-detail__evidence-item dl div { grid-template-columns: 1fr; gap: 2px; } }
</style>
