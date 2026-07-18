<script setup>
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElMessage } from 'element-plus';
import groupTagApi from '@/api/group-tag-api';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';

const emit = defineEmits(['submitted']);
const { visible, open, close, beforeClose, forceClose } = useDialog({
  isDirty: () => isDirty.value,
  isBusy: () => submitting.value,
});
const { formRef, mode, model, modelRules, submitting, isDirty, edit, submit } = useForm(
  () => ({ name: '' }),
  {
    rules: () => ({
      name: [{ required: true, message: '标签名称不能为空', trigger: 'blur' }],
    }),
    doSubmit(currentMode) {
      const payload = { name: model.value.name };
      return currentMode === 'create'
        ? groupTagApi.create(payload)
        : groupTagApi.replace(model.value.id, payload);
    },
    onSuccess(currentMode) {
      ElMessage.success(`${currentMode === 'create' ? '新增' : '修改'}成功`);
      emit('submitted');
      forceClose();
    },
    onFailure() {
      ElMessage.error('保存项目组标签失败，请稍后重试');
    },
  },
);

defineExpose({
  edit(existing) {
    edit(existing ? { id: existing.id, name: existing.name } : undefined);
    open();
  },
});
</script>

<template>
  <ElDialog
    v-model="visible"
    class="write-form-dialog write-form-dialog--compact"
    :title="mode === 'create' ? '新增项目组标签' : '修改项目组标签'"
    :before-close="beforeClose">
    <template #header>
      <div class="write-form-dialog__heading">
        <h2>{{ mode === 'create' ? '新增项目组标签' : '修改项目组标签' }}</h2>
      </div>
    </template>
    <ElForm
      ref="formRef"
      class="write-form write-form-grid write-form-grid--single"
      :model="model"
      :rules="modelRules"
      label-position="top">
      <div class="write-form-section">标签信息</div>
      <ElFormItem
        label="标签名称"
        prop="name">
        <ElInput
          v-model="model.name"
          maxlength="128"
          show-word-limit />
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="close">取消</ElButton>
      <ElButton
        type="primary"
        :loading="submitting"
        @click="submit">
        {{ submitting ? (mode === 'create' ? '创建中…' : '保存中…') : (mode === 'create' ? '创建标签' : '保存修改') }}
      </ElButton>
    </template>
  </ElDialog>
</template>
