<script setup>
import { ElButton, ElForm, ElMessage } from 'element-plus';
import { ref } from 'vue';
import configApi from '@/api/config-api';
import StorageAlertRuleForm from '@/components/form/StorageAlertRuleForm.vue';
import { defaultStorageAlertRule } from '@/utils/storage-alert-rule';
import { useStorageAlertThresholds } from '@/stores/storage-alert-thresholds';

const form = ref({ storage_alert_rule: defaultStorageAlertRule() });
const alertRuleValid = ref(true);
const saving = ref(false);
const alertThresholds = useStorageAlertThresholds();

function fetchConfig() {
  configApi.fetch().then((result) => {
    form.value = result;
  });
}

async function updateConfig() {
  if (saving.value) return;
  saving.value = true;
  try {
    form.value = await configApi.updateConfig(form.value);
    alertThresholds.setFromRule(form.value.storage_alert_rule);
    ElMessage.success('系统设置已保存');
  } finally {
    saving.value = false;
  }
}

fetchConfig();
</script>

<template>
  <section class="write-form-page">
    <div class="write-form-page__body">
      <h2>系统设置</h2>
      <ElForm
        class="write-form write-form-grid write-form-grid--single"
        label-position="top">
        <StorageAlertRuleForm
          v-if="form.storage_alert_rule"
          v-model="form.storage_alert_rule"
          @validity-change="alertRuleValid = $event" />
      </ElForm>
    </div>
    <div class="write-form-page__actions">
      <ElButton
        type="primary"
        :loading="saving"
        :disabled="!alertRuleValid"
        @click="updateConfig">
        {{ saving ? '保存中…' : '保存设置' }}
      </ElButton>
    </div>
  </section>
</template>
