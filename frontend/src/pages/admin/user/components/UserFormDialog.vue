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
  department: '',
  is_alert: true,
  user_type: 2,
}), {
  rules: () => ({
    rd_username: [
      { required: true, whitespace: true, message: '用户名不能为空', trigger: 'blur' },
    ],
    email: [
      { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
    ],
  }),
  doSubmit(mode) {
    const editable = {
      username: model.value.username?.trim() || null,
      email: model.value.email?.trim() || null,
      department: model.value.department?.trim() || null,
      user_type: model.value.user_type,
      is_alert: model.value.is_alert,
    };
    return (mode === 'create'
      ? usersApi.create({
        rd_username: model.value.rd_username.trim(),
        ...editable,
      })
      : usersApi.replace(model.value.id, editable));
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
        label="用户名"
        prop="rd_username">
        <ElInput
          v-model="model.rd_username"
          clearable
          :disabled="mode !== 'create'" />
      </ElFormItem>
      <ElFormItem
        label="姓名"
        prop="username">
        <ElInput
          v-model="model.username"
          clearable />
      </ElFormItem>
      <ElFormItem
        label="邮箱"
        prop="email">
        <ElInput
          v-model="model.email"
          clearable />
      </ElFormItem>
      <ElFormItem
        label="部门"
        prop="department">
        <ElInput
          v-model="model.department"
          clearable />
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
        label="告警状态"
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
