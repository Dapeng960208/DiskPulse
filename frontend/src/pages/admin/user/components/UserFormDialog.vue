<script setup>
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElMessage, ElSelect, ElOption, ElSwitch } from 'element-plus';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import usersApi from '@/api/users-api';
const emit = defineEmits(['submitted']);

const { visible, open, close, beforeClose, forceClose } = useDialog({
  isDirty: () => isDirty.value,
  isBusy: () => submitting.value,
});
const {
  formRef,
  mode,
  model,
  modelRules,
  submitting,
  isDirty,
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
    forceClose();
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
    class="write-form-dialog"
    :title="mode === 'create' ? '新增用户' : '修改用户'"
    :before-close="beforeClose"
    @close="formRef.clearValidate()">
    <template #header>
      <div class="write-form-dialog__heading">
        <h2>{{ mode === 'create' ? '新增用户' : '修改用户' }}</h2>
        <p>维护用户身份信息、账户类型和告警状态。</p>
      </div>
    </template>
    <ElForm
      ref="formRef"
      class="write-form write-form-grid"
      label-position="top"
      :model="model"
      :rules="modelRules"
    >
      <div class="write-form-section">身份信息</div>
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
      <div class="write-form-section">账户设置</div>
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
        {{ submitting ? (mode === 'create' ? '创建中…' : '保存中…') : (mode === 'create' ? '创建用户' : '保存修改') }}
      </ElButton>
    </template>
  </ElDialog>
</template>
