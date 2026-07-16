<script setup>
import { computed, ref } from 'vue';
import {
  ElAlert, ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElMessage,
  ElOption, ElSelect, ElSwitch,
} from 'element-plus';
import groupApi from '@/api/group-api';
import projectApi from '@/api/project-api';
import configApi from '@/api/config-api';
import storageClusterApi from '@/api/storage-cluster-api';
import GroupTagSelect from '@/components/form/GroupTagSelect.vue';
import MailSelect from '@/components/form/MailSelect.vue';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import QtreeSelect from '@/components/form/QtreeSelect.vue';
import RdUserSelect from '@/components/form/RdUserSelect.vue';
import StorageClusterSelect from '@/components/form/StorageClusterSelect.vue';
import VolumeSelect from '@/components/form/VolumeSelect.vue';
import StorageAlertRuleForm from '@/components/form/StorageAlertRuleForm.vue';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import { defaultStorageAlertRule } from '@/utils/storage-alert-rule';

const emit = defineEmits(['submitted']);
const { visible, open, close, beforeClose, forceClose } = useDialog({
  isDirty: () => isDirty.value,
  isBusy: () => submitting.value,
});
const selectedCluster = ref(null);
const selectedProject = ref(null);
const systemRule = ref(defaultStorageAlertRule());
const customAlertRule = ref(false);
const alertRuleValid = ref(true);

function initialModel() {
  return {
    name: '', project_id: null, storage_cluster_id: null, group_tag_id: null,
    target_type: null, volume_id: null, qtree_id: null, linux_path: null,
    back_path: null, enable_monitoring: true, associate_multiple_groups: false,
    in_charge_user_id: null, monitor_host_id: null, associated_mail_groups: [],
    storage_alert_rule: null, alert_cc_user_ids: [],
  };
}

const { formRef, mode, model, modelRules, submitting, isDirty, edit: editForm, submit } = useForm(initialModel, {
  rules: (currentModel) => ({
    name: [{ required: true, message: '名称不能为空', trigger: 'blur' }],
    project_id: [{ type: 'number', required: true, message: '关联项目不能为空', trigger: 'change' }],
    storage_cluster_id: [{ type: 'number', required: true, message: '存储集群不能为空', trigger: 'change' }],
    group_tag_id: [{ type: 'number', required: true, message: '项目组标签不能为空', trigger: 'change' }],
    target_type: [{ required: true, message: '目标类型不能为空', trigger: 'change' }],
    ...(currentModel.value.target_type === 'volume'
      ? { volume_id: [{ type: 'number', required: true, message: '存储空间不能为空', trigger: 'change' }] }
      : { qtree_id: [{ type: 'number', required: true, message: 'Qtree（NetApp）不能为空', trigger: 'change' }] }),
    linux_path: [{ required: true, message: '关联Linux路径不能为空', trigger: 'blur' }],
  }),
  doSubmit(currentMode) {
    const payload = { ...model.value };
    payload.project_id = model.value.project_id;
    payload.storage_cluster_id = model.value.storage_cluster_id;
    payload.group_tag_id = model.value.group_tag_id;
    delete payload.id;
    delete payload.project;
    delete payload.storage_cluster;
    delete payload.group_tag;
    delete payload.storage_target;
    delete payload.qtree;
    delete payload.in_charge_user;
    if (payload.target_type === 'volume') delete payload.qtree_id;
    if (payload.target_type === 'qtree') delete payload.volume_id;
    delete payload.target_type;
    return currentMode === 'create' ? groupApi.create(payload) : groupApi.replace(model.value.id, payload);
  },
  onSuccess(currentMode) {
    ElMessage.success(`${currentMode === 'create' ? '新增' : '修改'}成功`);
    emit('submitted');
    forceClose();
  },
  onFailure() { ElMessage.error('保存项目组失败，请稍后重试'); },
});

const isNetApp = computed(() => selectedCluster.value?.storage_type === 'netapp');
const inheritedRule = computed(() => selectedProject.value?.storage_alert_rule || systemRule.value);
const inheritedRuleSource = computed(() => selectedProject.value?.storage_alert_rule ? '项目规则' : '系统规则');

async function loadSystemRule() {
  try {
    const config = await configApi.fetch();
    systemRule.value = config.storage_alert_rule || defaultStorageAlertRule();
  } catch {
    systemRule.value = defaultStorageAlertRule();
  }
}

async function changeProject(projectId) {
  model.value.project_id = projectId;
  await loadProject(projectId);
}

async function loadProject(projectId, fallback = null) {
  try {
    selectedProject.value = projectId ? await projectApi.fetchById(projectId) : null;
  } catch {
    selectedProject.value = fallback;
  }
}

function changeCustomAlertRule(enabled) {
  customAlertRule.value = enabled;
  model.value.storage_alert_rule = enabled ? defaultStorageAlertRule() : null;
}

async function changeCluster(clusterId) {
  model.value.storage_cluster_id = clusterId;
  model.value.volume_id = null;
  model.value.qtree_id = null;
  selectedCluster.value = clusterId ? await storageClusterApi.fetchById(clusterId) : null;
  model.value.target_type = selectedCluster.value?.storage_type === 'isilon' ? 'volume' : null;
}

function changeTargetType(value) {
  model.value.target_type = value;
  model.value.volume_id = null;
  model.value.qtree_id = null;
}

defineExpose({
  edit(existing) {
    void loadSystemRule();
    if (!existing) {
      selectedCluster.value = null;
      selectedProject.value = null;
      customAlertRule.value = false;
      editForm();
    } else {
      customAlertRule.value = existing.storage_alert_rule != null;
      editForm({
        ...initialModel(), ...existing,
        project_id: existing.project_id ?? existing.project?.id,
        storage_cluster_id: existing.storage_cluster_id ?? existing.storage_cluster?.id,
        group_tag_id: existing.group_tag_id ?? existing.group_tag?.id,
        target_type: existing.storage_target?.type
          ?? (existing.volume_id != null ? 'volume' : 'qtree'),
      });
      selectedCluster.value = existing.storage_cluster ?? null;
      selectedProject.value = null;
      void loadProject(model.value.project_id, existing.project ?? null);
      if (!selectedCluster.value && model.value.storage_cluster_id) {
        storageClusterApi.fetchById(model.value.storage_cluster_id)
          .then((cluster) => { selectedCluster.value = cluster; })
          .catch(() => { selectedCluster.value = null; });
      }
    }
    open();
  },
});
</script>

<template>
  <ElDialog
    v-model="visible"
    class="write-form-dialog"
    :title="mode === 'create' ? '新增项目组监控配置' : '修改项目组监控配置'"
    :before-close="beforeClose"
    @close="formRef.clearValidate()">
    <template #header>
      <div class="write-form-dialog__heading">
        <h2>{{ mode === 'create' ? '新增项目组监控配置' : '修改项目组监控配置' }}</h2>
        <p>配置项目归属、存储目标、负责人和告警策略。</p>
      </div>
    </template>
    <ElForm
      ref="formRef"
      class="write-form write-form-grid"
      :model="model"
      :rules="modelRules"
      label-position="top">
      <div class="write-form-section">基本信息</div>
      <ElFormItem
        label="组名"
        prop="name"><ElInput v-model="model.name" /></ElFormItem>
      <ElFormItem
        label="关联项目"
        prop="project_id"><ProjectSelect
          :model-value="model.project_id"
          @update:model-value="changeProject" /></ElFormItem>
      <ElFormItem
        label="存储集群"
        prop="storage_cluster_id">
        <StorageClusterSelect
          :model-value="model.storage_cluster_id"
          @update:model-value="changeCluster" />
      </ElFormItem>
      <ElFormItem
        label="项目组标签"
        prop="group_tag_id"><GroupTagSelect v-model="model.group_tag_id" /></ElFormItem>
      <div class="write-form-section">存储目标</div>
      <ElFormItem
        v-if="isNetApp"
        label="目标类型"
        prop="target_type">
        <ElSelect
          :model-value="model.target_type"
          @update:model-value="changeTargetType">
          <ElOption
            label="存储空间"
            value="volume" /><ElOption
              label="Qtree（NetApp）"
              value="qtree" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem
        v-else-if="selectedCluster"
        label="目标类型">存储空间（Directory Quota）</ElFormItem>
      <ElFormItem
        v-if="selectedCluster && model.target_type === 'volume'"
        :label="isNetApp ? '存储空间' : '存储空间（Directory Quota）'"
        prop="volume_id">
        <VolumeSelect
          v-model="model.volume_id"
          :storage-cluster-id="model.storage_cluster_id" />
      </ElFormItem>
      <ElFormItem
        v-if="selectedCluster && model.target_type === 'qtree'"
        label="Qtree（NetApp）"
        prop="qtree_id">
        <QtreeSelect
          v-model="model.qtree_id"
          :storage-cluster-id="model.storage_cluster_id" />
      </ElFormItem>
      <ElFormItem
        class="write-form-field--full"
        label="关联Linux路径"
        prop="linux_path"><ElInput v-model="model.linux_path" /></ElFormItem>
      <div class="write-form-section">负责人和通知</div>
      <ElFormItem label="单个存储目标关联多个项目组"><ElSwitch v-model="model.associate_multiple_groups" /></ElFormItem>
      <ElFormItem label="项目组开发代表"><RdUserSelect
        v-model="model.in_charge_user_id"
        clearable /></ElFormItem>
      <ElFormItem label="关联群组/个人邮箱"><MailSelect
        v-model="model.associated_mail_groups"
        type="distribution"
        multiple /></ElFormItem>
      <div class="write-form-section">监控和告警</div>
      <ElFormItem label="是否监控"><ElSwitch v-model="model.enable_monitoring" /></ElFormItem>
      <ElFormItem label="自定义告警规则">
        <ElSwitch
          :model-value="customAlertRule"
          @update:model-value="changeCustomAlertRule" />
      </ElFormItem>
      <template v-if="model.enable_monitoring">
        <ElAlert
          v-if="!customAlertRule"
          class="write-form-field--full"
          :title="`继承${inheritedRuleSource}`"
          type="info"
          :closable="false" />
        <StorageAlertRuleForm
          v-if="customAlertRule"
          v-model="model.storage_alert_rule"
          class="write-form-field--full"
          @validity-change="alertRuleValid = $event" />
        <StorageAlertRuleForm
          v-else
          class="write-form-field--full"
          :model-value="inheritedRule"
          disabled />
      </template>
      <ElFormItem label="飞书个人抄送">
        <RdUserSelect
          v-model="model.alert_cc_user_ids"
          clearable
          multiple />
      </ElFormItem>
      <ElFormItem label="是否已结项"><ElSwitch v-model="model.completed" /></ElFormItem>
      <ElFormItem
        v-if="false"
        label="是否开启离职数据备份"><ElSwitch v-model="model.back_up_enabled" /></ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="close">取消</ElButton><ElButton
        type="primary"
        :loading="submitting"
        :disabled="customAlertRule && !alertRuleValid"
        @click="submit">
        {{ submitting ? (mode === 'create' ? '创建中…' : '保存中…') : (mode === 'create' ? '创建项目组' : '保存修改') }}
      </ElButton>
    </template>
  </ElDialog>
</template>
