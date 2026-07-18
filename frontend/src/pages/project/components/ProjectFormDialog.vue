<script setup>
import { ElAlert, ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElMessage, ElSwitch } from 'element-plus';
import { ref } from 'vue';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import projectApi from '@/api/project-api';
import configApi from '@/api/config-api';
import RdUserSelect  from '@/components/form/RdUserSelect.vue';
import StorageAlertRuleForm from '@/components/form/StorageAlertRuleForm.vue';
import { defaultStorageAlertRule } from '@/utils/storage-alert-rule';
const emit = defineEmits(['submitted']);
const { visible, open, close, beforeClose, forceClose } = useDialog({
  isDirty: () => isDirty.value,
  isBusy: () => submitting.value,
});
const customAlertRule = ref(false);
const alertRuleValid = ref(true);
const systemRule = ref(defaultStorageAlertRule());
const initialModel = () => ({ description: '', is_alert: true, storage_alert_rule: null });
const {
  formRef,
  mode,
  model,
  modelRules,
  submitting,
  isDirty,
  edit: editForm,
  submit,
} = useForm(initialModel, {
  rules: (model) => ({
    name: [
      { type: 'string', required: true, message: '名称不能为空', trigger: 'blur' },
    ],
  }),
  doSubmit(mode) {
      const modelValue = {
        ...model.value,
      };
      return (mode === 'create'
        ? projectApi.create(modelValue)
        : projectApi.replace(modelValue.id, modelValue))
  },
  onSuccess(mode) {
    ElMessage.success(`${mode === 'create' ? '新增' : '修改'}成功`);
    emit('submitted');
    forceClose();
  },
  onFailure() { ElMessage.error('保存项目失败，请稍后重试'); },
});

function changeCustomAlertRule(enabled) {
  customAlertRule.value = enabled;
  model.value.storage_alert_rule = enabled ? defaultStorageAlertRule() : null;
}

async function loadSystemRule() {
  try {
    const config = await configApi.fetch();
    systemRule.value = config.storage_alert_rule || defaultStorageAlertRule();
  } catch {
    systemRule.value = defaultStorageAlertRule();
  }
}

defineExpose({
  edit(existing) {
    void loadSystemRule();
    if (existing) {
      customAlertRule.value = existing.storage_alert_rule != null;
      editForm({ ...initialModel(), ...existing, is_alert: existing.is_alert ?? true });
    } else {
      customAlertRule.value = false;
      editForm();
    }
    open();
  },
});
</script>

<template>
  <ElDialog
    v-model="visible"
    class="write-form-dialog"
    :title="mode === 'create' ? '新增项目' : '修改项目'"
    :before-close="beforeClose"
    @close="formRef.clearValidate()">
    <template #header>
      <div class="write-form-dialog__heading">
        <h2>{{ mode === 'create' ? '新增项目' : '修改项目' }}</h2>
        <p>维护项目负责人、说明和告警策略。</p>
      </div>
    </template>
    <ElForm
      ref="formRef"
      class="write-form write-form-grid"
      label-position="top"
      :model="model"
      :rules="modelRules"
    >
      <div class="write-form-section">基本信息</div>
      <ElFormItem
        label="项目名"
        prop="name">
        <ElInput v-model="model.name" />
      </ElFormItem>
      <ElFormItem
        label="项目负责人"
        prop="in_charge_user_id">
        <RdUserSelect v-model="model.in_charge_user_id" />
      </ElFormItem>
      <ElFormItem
        class="write-form-field--full"
        label="描述"
        prop="description">
        <ElInput
          v-model="model.description"
          type="textarea" />
      </ElFormItem>
      <div class="write-form-section">告警设置</div>
      <ElFormItem label="项目告警">
        <ElSwitch v-model="model.is_alert" />
      </ElFormItem>
      <ElFormItem label="自定义告警规则">
        <ElSwitch
          :model-value="customAlertRule"
          @update:model-value="changeCustomAlertRule" />
      </ElFormItem>
      <template v-if="model.is_alert">
        <ElAlert
          v-if="!customAlertRule"
          class="write-form-field--full"
          title="继承系统规则"
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
          :model-value="systemRule"
          disabled />
      </template>
    </ElForm>
    <template #footer>
      <ElButton
        :disabled="submitting"
        @click="close">
        取消
      </ElButton>
      <ElButton
        type="primary"
        :loading="submitting"
        :disabled="customAlertRule && !alertRuleValid"
        @click="submit">
        {{ submitting ? (mode === 'create' ? '创建中…' : '保存中…') : (mode === 'create' ? '创建项目' : '保存修改') }}
      </ElButton>
    </template>
  </ElDialog>
</template>
