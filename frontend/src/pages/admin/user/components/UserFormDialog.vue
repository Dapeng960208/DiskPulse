<script setup>
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElMessage, ElSelect, ElOption, ElSwitch } from 'element-plus';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import usersApi from '@/api/users-api';
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
  rd_username: '',
  username: '',
  email: '',
  is_alert: true,
  user_group_ids: [],
  user_type: 2, // Default to '在职账户'
}), {
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
      ? usersApi.create(modelValue)
      : usersApi.replace(modelValue.id, modelValue));
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
    :title="mode === 'create' ? '新增用户' : '修改用户'"
    @close="formRef.clearValidate()">
    <ElForm
      ref="formRef"
      label-width="100px"
      :model="model"
      :rules="modelRules"
    >
      <ElFormItem
        label="研发用户名"
        prop="rd_username">
        <ElInput
          v-model="model.rd_username"
          clearable
          :disabled="true" />
      </ElFormItem>
      <ElFormItem
        label="域控用户名"
        prop="username">
        <ElInput
          v-model="model.username"
          clearable
          :disabled="model.user_type === 2" />
      </ElFormItem>
      <ElFormItem
        label="邮箱"
        prop="email">
        <ElInput
          v-model="model.email"
          clearable
          :disabled="model.user_type === 2" />
      </ElFormItem>
      <ElFormItem
        label="账户类型"
        prop="user_type">
        <ElSelect
          v-model="model.user_type"
          placeholder="请选择账户类型">
          <ElOption
            label="离职账户"
            :value="0" />
          <ElOption
            label="公共账户"
            :value="1" />
          <ElOption
            label="在职账户"
            :value="2" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem
        label="是否告警"
        prop="is_alert">
        <ElSwitch v-model="model.is_alert" />
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
