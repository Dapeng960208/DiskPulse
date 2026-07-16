<script setup>
import { computed, watch } from 'vue';
import { ElAlert, ElFormItem, ElInputNumber, ElOption, ElSelect } from 'element-plus';

const props = defineProps({
  modelValue: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue', 'validity-change']);

const levels = [
  { key: 'important', label: '重要' },
  { key: 'serious', label: '严重' },
  { key: 'emergency', label: '紧急' },
];

const validationMessage = computed(() => {
  const rule = props.modelValue;
  if (!rule || !['hard', 'soft'].includes(rule.quota_basis)) return '请选择有效的限额口径';
  if (!levels.every(({ key }) => Number.isInteger(rule[key]?.threshold)
    && rule[key].threshold > 0 && rule[key].threshold <= 100)) return '阈值必须是 1 到 100 的整数';
  if (rule.important.threshold >= rule.serious.threshold) return '重要阈值必须小于严重阈值';
  if (rule.serious.threshold >= rule.emergency.threshold) return '严重阈值必须小于紧急阈值';
  if (!levels.every(({ key }) => Number.isInteger(rule[key]?.repeat_hours)
    && rule[key].repeat_hours > 0)) return '重复通知频次必须是正整数';
  return '';
});

watch(validationMessage, (message) => emit('validity-change', !message), { immediate: true });

function updateBasis(quotaBasis) {
  emit('update:modelValue', { ...props.modelValue, quota_basis: quotaBasis });
}

function updateLevel(level, field, value) {
  emit('update:modelValue', {
    ...props.modelValue,
    [level]: { ...props.modelValue[level], [field]: value },
  });
}
</script>

<template>
  <div class="storage-alert-rule-form">
    <ElFormItem label="限额口径">
      <ElSelect
        :model-value="modelValue.quota_basis"
        :disabled="disabled"
        @update:model-value="updateBasis">
        <ElOption
          label="硬限额"
          value="hard" />
        <ElOption
          label="软限额"
          value="soft" />
      </ElSelect>
    </ElFormItem>
    <div
      v-for="level in levels"
      :key="level.key"
      class="storage-alert-rule-form__level">
      <strong>{{ level.label }}</strong>
      <ElFormItem label="阈值（%）">
        <ElInputNumber
          :model-value="modelValue[level.key].threshold"
          :disabled="disabled"
          :min="1"
          :max="100"
          :step="1"
          @update:model-value="updateLevel(level.key, 'threshold', $event)" />
      </ElFormItem>
      <ElFormItem label="重复通知频次（小时）">
        <ElInputNumber
          :model-value="modelValue[level.key].repeat_hours"
          :disabled="disabled"
          :min="1"
          :step="1"
          @update:model-value="updateLevel(level.key, 'repeat_hours', $event)" />
      </ElFormItem>
    </div>
    <ElAlert
      v-if="validationMessage"
      :title="validationMessage"
      type="error"
      :closable="false" />
  </div>
</template>

<style scoped>
.storage-alert-rule-form__level {
  display: grid;
  grid-template-columns: 70px minmax(180px, 1fr) minmax(220px, 1fr);
  gap: var(--spacing-md);
  align-items: center;
}
</style>
