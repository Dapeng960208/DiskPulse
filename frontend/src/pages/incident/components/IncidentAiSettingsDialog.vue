<template>
  <ElDialog
    v-model="visible"
    title="事件 AI 设置"
    width="600px"
    :close-on-click-modal="false"
    @close="handleClose">
    <div
      v-if="loading"
      style="text-align: center; padding: 40px">
      <ElIcon class="is-loading">
        <Loading />
      </ElIcon>
      <div style="margin-top: 10px">
        加载中...
      </div>
    </div>
    <div v-else>
      <ElAlert
        v-if="error"
        type="error"
        :closable="false"
        style="margin-bottom: 15px">
        {{ error }}
      </ElAlert>
      <ElForm label-width="140px">
        <ElFormItem
          label="启用 AI 代理">
          <ElSwitch
            :model-value="settings.enabled"
            @update:model-value="$emit('update:settings', { ...settings, enabled: $event })" />
        </ElFormItem>
        <ElFormItem
          label="AI 模型"
          :required="settings.enabled">
          <ElSelect
            :model-value="settings.model_ids"
            multiple
            placeholder="选择 AI 模型（按优先级排序）"
            style="width: 100%"
            :disabled="!settings.enabled"
            @update:model-value="$emit('update:settings', { ...settings, model_ids: $event })">
            <ElOption
              v-for="model in settings.available_models"
              :key="model.id"
              :label="`${model.name} (${model.provider})`"
              :value="model.id" />
          </ElSelect>
          <div style="color: #909399; font-size: 12px; margin-top: 5px">
            已选择模型将按顺序尝试，直到成功
          </div>
        </ElFormItem>
        <ElFormItem
          label="IOPS 绝对下限"
          :required="settings.enabled">
          <ElInputNumber
            :model-value="settings.iops_absolute_floor"
            :min="0"
            :max="1000"
            :step="1"
            :disabled="!settings.enabled"
            style="width: 200px"
            @update:model-value="$emit('update:settings', { ...settings, iops_absolute_floor: $event })" />
          <div style="color: #909399; font-size: 12px; margin-top: 5px">
            IOPS 低于此值将被视为噪声（默认 10）
          </div>
        </ElFormItem>
        <ElFormItem
          label="IOPS 基线比例"
          :required="settings.enabled">
          <ElInputNumber
            :model-value="settings.iops_baseline_ratio"
            :min="0"
            :max="1"
            :step="0.01"
            :precision="2"
            :disabled="!settings.enabled"
            style="width: 200px"
            @update:model-value="$emit('update:settings', { ...settings, iops_baseline_ratio: $event })" />
          <div style="color: #909399; font-size: 12px; margin-top: 5px">
            相对基线的噪声门槛（默认 0.05 = 5%）
          </div>
        </ElFormItem>
        <ElFormItem label="已选择模型">
          <div
            v-if="selectedModels.length === 0"
            style="color: #909399">
            未选择模型
          </div>
          <ElTag
            v-for="(model, index) in selectedModels"
            :key="model.id"
            type="info"
            style="margin-right: 8px; margin-bottom: 8px">
            {{ index + 1 }}. {{ model.name }}
          </ElTag>
        </ElFormItem>
      </ElForm>
    </div>
    <template #footer>
      <ElButton @click="handleClose">
        取消
      </ElButton>
      <ElButton
        type="primary"
        :loading="saving"
        :disabled="loading"
        @click="handleSave">
        保存
      </ElButton>
    </template>
  </ElDialog>
</template>

<script setup>
import { computed } from 'vue';
import {
  ElAlert,
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTag,
} from 'element-plus';
import { Loading } from '@element-plus/icons-vue';

const props = defineProps({
  visible: { type: Boolean, required: true },
  loading: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  error: { type: String, default: '' },
  settings: { type: Object, required: true },
  selectedModels: { type: Array, default: () => [] },
});

const emit = defineEmits(['update:visible', 'update:settings', 'save', 'close']);

const visible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
});

function handleSave() {
  emit('save');
}

function handleClose() {
  emit('close');
}
</script>
