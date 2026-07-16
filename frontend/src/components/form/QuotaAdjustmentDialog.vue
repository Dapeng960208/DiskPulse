<script setup>
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
} from 'element-plus';
import { computed, reactive, ref } from 'vue';
import groupApi from '@/api/group-api.js';
import storageUsageApi from '@/api/storage-usage-api.js';

const props = defineProps({
  resourceType: {
    type: String,
    required: true,
    validator: (value) => ['group', 'storage_usage'].includes(value),
  },
});
const emit = defineEmits(['submitted']);

const visible = ref(false);
const submitting = ref(false);
const formRef = ref();
const resource = ref();
const model = reactive({
  hard_limit: null,
  soft_limit: null,
  unit: 'GiB',
  soft_grace: null,
  soft_grace_unit: 'days',
});

const storageType = computed(() => resource.value?.storage_cluster?.storage_type?.toLowerCase());
const isIsilon = computed(() => storageType.value === 'isilon');
const supportsSoftLimit = computed(() => !(
  props.resourceType === 'group'
  && storageType.value === 'netapp'
  && resource.value?.storage_target?.type?.toLowerCase() === 'volume'
));
const title = computed(() => props.resourceType === 'group' ? '调整项目组配额' : '调整用户配额');

const rules = {
  hard_limit: [
    { required: true, message: '请输入硬限额', trigger: 'blur' },
    {
      validator: (_, value, callback) => {
        if (Number(value) > 0) callback();
        else callback(new Error('硬限额必须大于 0'));
      },
      trigger: 'blur',
    },
  ],
  soft_limit: [{
    validator: (_, value, callback) => {
      if (value == null || value === '') callback();
      else if (Number(value) <= 0) callback(new Error('软限额必须大于 0'));
      else if (Number(value) >= Number(model.hard_limit)) callback(new Error('软限额必须小于硬限额'));
      else callback();
    },
    trigger: 'blur',
  }],
  soft_grace: [{
    validator: (_, value, callback) => {
      if (!isIsilon.value || model.soft_limit == null || Number(value) > 0) callback();
      else callback(new Error('设置软限额时必须填写宽限期'));
    },
    trigger: 'blur',
  }],
};

function open(row) {
  resource.value = row;
  Object.assign(model, {
    hard_limit: row.limit ?? null,
    soft_limit: supportsSoftLimit.value ? (row.soft_limit ?? null) : null,
    unit: 'GiB',
    soft_grace: null,
    soft_grace_unit: 'days',
  });
  visible.value = true;
}

function toGiB(value) {
  return Number(value) * (model.unit === 'TiB' ? 1024 : 1);
}

async function submit() {
  await formRef.value?.validate();
  if (resource.value?.limit && toGiB(model.hard_limit) < Number(resource.value.limit)) {
    await ElMessageBox.confirm(
      '新的硬限额低于当前硬限额，确认继续缩减配额？',
      '确认缩减配额',
      { type: 'warning', confirmButtonText: '继续调整', cancelButtonText: '取消' },
    );
  }

  const payload = {
    hard_limit: model.hard_limit,
    soft_limit: supportsSoftLimit.value ? model.soft_limit : null,
    unit: model.unit,
    soft_grace: isIsilon.value && model.soft_limit != null ? model.soft_grace : null,
    soft_grace_unit: isIsilon.value && model.soft_limit != null ? model.soft_grace_unit : null,
  };
  const api = props.resourceType === 'group' ? groupApi : storageUsageApi;
  submitting.value = true;
  try {
    await api.adjustQuota(resource.value.id, payload);
    ElMessage.success('配额调整成功');
    visible.value = false;
    emit('submitted');
  } finally {
    submitting.value = false;
  }
}

defineExpose({ open, model });
</script>

<template>
  <ElDialog
    v-model="visible"
    :title="title"
    width="560px">
    <div class="quota-summary">
      <span>对象：{{ resource?.name || resource?.user?.rd_username || '-' }}</span>
      <span>存储：{{ resource?.storage_cluster?.storage_type || '-' }}</span>
    </div>
    <ElForm
      ref="formRef"
      :model="model"
      :rules="rules"
      label-width="120px">
      <ElFormItem
        label="硬限额"
        prop="hard_limit">
        <ElInputNumber
          v-model="model.hard_limit"
          :min="0.01"
          :precision="2"
          controls-position="right" />
        <ElSelect
          v-model="model.unit"
          class="quota-unit">
          <ElOption label="GiB" value="GiB" />
          <ElOption label="TiB" value="TiB" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem
        v-if="supportsSoftLimit"
        label="软限额（可选）"
        prop="soft_limit">
        <ElInputNumber
          v-model="model.soft_limit"
          :min="0.01"
          :precision="2"
          controls-position="right" />
        <span class="quota-unit-text">{{ model.unit }}</span>
      </ElFormItem>
      <ElFormItem
        v-if="isIsilon"
        label="软限额宽限期"
        prop="soft_grace">
        <ElInputNumber
          v-model="model.soft_grace"
          :min="1"
          :precision="0"
          :disabled="model.soft_limit == null"
          controls-position="right" />
        <ElSelect
          v-model="model.soft_grace_unit"
          :disabled="model.soft_limit == null"
          class="quota-unit">
          <ElOption label="分钟" value="minutes" />
          <ElOption label="小时" value="hours" />
          <ElOption label="天" value="days" />
        </ElSelect>
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="visible = false">取消</ElButton>
      <ElButton
        type="primary"
        :loading="submitting"
        @click="submit">确认调整</ElButton>
    </template>
  </ElDialog>
</template>

<style scoped>
.quota-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
  color: var(--el-text-color-secondary);
}

.quota-unit {
  width: 110px;
  margin-left: 12px;
}

.quota-unit-text {
  margin-left: 12px;
  color: var(--el-text-color-secondary);
}
</style>
