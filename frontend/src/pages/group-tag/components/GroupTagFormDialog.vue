<script setup>
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElMessage } from 'element-plus';
import groupTagApi from '@/api/group-tag-api';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';

const emit = defineEmits(['submitted']);
const { visible, open, close } = useDialog();
const { formRef, mode, model, modelRules, submitting, edit, submit } = useForm(
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
      close();
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
    :title="mode === 'create' ? '新增项目组标签' : '修改项目组标签'">
    <ElForm
      ref="formRef"
      :model="model"
      :rules="modelRules"
      label-width="100">
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
        @click="submit">提交</ElButton>
    </template>
  </ElDialog>
</template>
