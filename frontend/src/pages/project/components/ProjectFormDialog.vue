<script setup>
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElMessage, ElSwitch } from 'element-plus';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import projectApi from '@/api/project-api';
import RdUserSelect  from '@/components/form/RdUserSelect.vue';
const emit = defineEmits(['submitted']);
const { visible, open, close } = useDialog();
const {
  formRef,
  mode,
  model,
  modelRules,
  submitting,
  edit,
  submit,
} = useForm(() => ({
  description: '',
}), {
  rules: (model) => ({
    name: [
      { type: 'string', required: true, message: '名称不能为空', trigger: 'blur' },
    ],
    // pt_user_id: [
    //   { type: 'number', required: true, message: 'PT经理不能为空', trigger: 'blur' },
    // ],
    // in_charge_user_id: [
    //   { type: 'number', required: true, message: '开发代表不能为空', trigger: 'blur' },
    // ],
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
    close();
  },
});

defineExpose({
  edit(existing) {
    if (existing) {
      edit({
        ...existing,
      });
    } else {
      edit();
    }
    open();
  },
});
</script>

<template>
  <ElDialog
    v-model="visible"
    :title="mode === 'create' ? '新增项目' : '修改项目'"
    @close="formRef.clearValidate()">
    <ElForm
      ref="formRef"
      label-width="100px"
      :model="model"
      :rules="modelRules"
    >
      <ElFormItem
        label="项目名"
        prop="name">
        <ElInput v-model="model.name" />
      </ElFormItem>
      <ElFormItem
        label="PT经理"
        prop="pt_user_id">
        <RdUserSelect v-model="model.pt_user_id" />
      </ElFormItem>
      <ElFormItem
        label="开发代表"
        prop="in_charge_user_id">
        <RdUserSelect v-model="model.in_charge_user_id" />
      </ElFormItem>
      <ElFormItem
        label="描述"
        prop="description">
        <ElInput
          v-model="model.description"
          type="textarea" />
      </ElFormItem>
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
        @click="submit">
        提交
      </ElButton>
    </template>
  </ElDialog>
</template>
