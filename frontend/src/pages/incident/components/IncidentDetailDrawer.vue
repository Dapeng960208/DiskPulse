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
  ElTable,
  ElTableColumn,
  ElTag,
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
const nextStatus = computed(() => ({
  open: 'acknowledged',
  acknowledged: 'investigating',
  investigating: 'mitigated',
  mitigated: 'resolved',
})[current.value.status] || null);

const categoryLabels = {
  capacity_pressure: '容量压力',
  device_fault: '设备故障',
  performance_contention: '性能争用',
  telemetry_blindspot: '遥测盲区',
};

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

async function updateIncident(payload) {
  if (!current.value.id) return;
  try {
    await incidentApi.updateIncident(current.value.id, payload);
    await load();
    emit('updated');
  } catch {
    error.value = '更新事件失败，请确认当前项目权限后重试';
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
  } catch {
    error.value = '创建维护窗口失败，请确认项目管理员权限后重试';
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
        <ElDescriptionsItem label="资产">{{ current.display_name }}</ElDescriptionsItem>
        <ElDescriptionsItem label="类别">{{ categoryLabels[current.category] || current.category }}</ElDescriptionsItem>
        <ElDescriptionsItem label="状态">{{ current.status }}</ElDescriptionsItem>
        <ElDescriptionsItem label="严重度"><ElTag :type="current.severity === 'critical' ? 'danger' : 'warning'">{{ current.severity }}</ElTag></ElDescriptionsItem>
      </ElDescriptions>

      <div
        v-if="capabilities.edit"
        class="incident-detail__actions list-row-actions">
        <ElButton
          data-testid="incident-claim"
          size="small"
          @click="updateIncident({ claim: true })">认领</ElButton>
        <ElButton
          size="small"
          @click="updateIncident({ claim: false })">释放</ElButton>
        <ElButton
          v-if="nextStatus"
          type="primary"
          size="small"
          @click="updateIncident({ status: nextStatus })">推进为 {{ nextStatus }}</ElButton>
        <ElButton
          size="small"
          @click="updateIncident({ silenced_until: null })">取消静默</ElButton>
      </div>
      <div
        v-if="capabilities.create_maintenance_window"
        class="incident-detail__actions">
        <ElButton
          type="warning"
          plain
          size="small"
          @click="openMaintenance">创建维护窗口</ElButton>
      </div>

      <section class="incident-detail__section">
        <h3>确定性诊断</h3>
        <p v-if="!current.diagnosis">尚无足够证据生成诊断。</p>
        <template v-else>
          <p>置信度：<ElTag>{{ current.diagnosis.confidence }}</ElTag></p>
          <ul class="incident-detail__candidate-list">
            <li
              v-for="candidate in current.diagnosis.candidates || []"
              :key="candidate.category">
              {{ categoryLabels[candidate.category] || candidate.category }}：{{ candidate.score }}
              <span>证据 {{ (candidate.evidence_refs || []).join('、') || '无' }}</span>
              <span v-if="candidate.data_gaps?.length">；数据缺口 {{ candidate.data_gaps.join('、') }}</span>
            </li>
          </ul>
        </template>
      </section>

      <section class="incident-detail__section">
        <h3>证据摘要</h3>
        <ElTable
          :data="current.evidence || []"
          size="small"
          empty-text="暂无证据摘要">
          <ElTableColumn
            prop="evidence_type"
            label="类型"
            min-width="150" />
          <ElTableColumn
            prop="source"
            label="来源"
            min-width="120" />
          <ElTableColumn
            prop="source_ref"
            label="不可变引用"
            min-width="180" />
          <ElTableColumn
            prop="observed_at"
            label="观测时间"
            min-width="180" />
        </ElTable>
      </section>

      <section class="incident-detail__section">
        <h3>时间线</h3>
        <ElTable
          :data="current.timeline || []"
          size="small"
          empty-text="暂无操作记录">
          <ElTableColumn
            prop="occurred_at"
            label="时间"
            min-width="180" />
          <ElTableColumn
            prop="event_type"
            label="事件"
            min-width="130" />
          <ElTableColumn
            prop="comment"
            label="评论"
            min-width="200" />
        </ElTable>
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
.incident-detail__candidate-list { margin: 0; padding-left: 20px; color: var(--text-primary); }
.incident-detail__candidate-list span { color: var(--text-secondary); }
.incident-detail__comment { justify-self: end; }
</style>
