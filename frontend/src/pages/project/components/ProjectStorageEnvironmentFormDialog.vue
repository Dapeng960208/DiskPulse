<script setup>
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElSwitch,
} from 'element-plus';
import projectStorageEnvironmentApi from '@/api/project-storage-environment-api';
import StorageClusterSelect from '@/components/form/StorageClusterSelect.vue';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';

const props = defineProps({
  projectId: {
    type: Number,
    required: true,
  },
});
const emit = defineEmits(['submitted']);

const { visible, open, close } = useDialog();
const {
  formRef,
  mode,
  model,
  modelRules,
  submitting,
  edit: editForm,
  submit,
} = useForm(() => ({
  name: '',
  storage_cluster_id: null,
  description: '',
  is_active: true,
}), {
  rules: () => ({
    name: [
      { required: true, message: '环境名称不能为空', trigger: 'blur' },
      { max: 128, message: '环境名称不能超过 128 个字符', trigger: 'blur' },
    ],
    storage_cluster_id: [
      { required: true, message: '存储集群不能为空', trigger: 'change' },
    ],
  }),
  doSubmit(currentMode) {
    const name = model.value.name.trim();
    if (currentMode === 'create') {
      return projectStorageEnvironmentApi.createForProject(props.projectId, {
        name,
        storage_cluster_id: model.value.storage_cluster_id,
        description: model.value.description,
        is_active: model.value.is_active,
      });
    }
    return projectStorageEnvironmentApi.replace(model.value.id, {
      name,
      description: model.value.description,
      is_active: model.value.is_active,
    });
  },
  onSuccess(currentMode) {
    ElMessage.success(`${currentMode === 'create' ? '新增' : '修改'}成功`);
    emit('submitted');
    close();
  },
  onFailure() {
    ElMessage.error('保存存储环境失败，请稍后重试');
  },
});

function clearValidation() {
  formRef.value?.clearValidate();
}

defineExpose({
  create() {
    editForm();
    open();
  },
  edit(existing) {
    editForm({ ...existing });
    open();
  },
});
</script>

<template>
  <ElDialog
    v-model="visible"
    :title="mode === 'create' ? '新增存储环境' : '编辑存储环境'"
    @close="clearValidation">
    <ElForm
      ref="formRef"
      label-width="100"
      :model="model"
      :rules="modelRules">
      <ElFormItem
        label="环境名称"
        prop="name">
        <ElInput
          v-model="model.name"
          maxlength="128"
          clearable
          placeholder="请输入环境名称" />
      </ElFormItem>
      <ElFormItem
        v-if="mode === 'create'"
        label="存储集群"
        prop="storage_cluster_id">
        <StorageClusterSelect v-model="model.storage_cluster_id" />
      </ElFormItem>
      <ElFormItem
        label="描述"
        prop="description">
        <ElInput
          v-model="model.description"
          type="textarea"
          :rows="3"
          clearable
          placeholder="请输入描述信息" />
      </ElFormItem>
      <ElFormItem
        label="启用状态"
        prop="is_active">
        <ElSwitch v-model="model.is_active" />
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
