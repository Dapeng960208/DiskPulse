<script setup>
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElMessage } from 'element-plus';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import groupApi from '@/api/group-api';
import userApi from '@/api/users-api';
import storageUsageApi from '@/api/storage-usage-api';
import GroupSelect from '@/components/form/GroupSelect.vue';
import RdUserSelect from '@/components/form/RdUserSelect.vue';
import StorageClusterSelect from '@/components/form/StorageClusterSelect.vue';
import { ref, computed } from 'vue';

const number = 'number';
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
  group_id: null,
  user_id: null,
  linux_path: '',
}), {
  rules: (model) => ({
    group_id: [
      { type: number, required: true, message: '关联项目组不能为空', trigger: 'blur' },
    ],
    user_id: [
      { type: number, required: true, message: '关联用户不能为空', trigger: 'blur' },
    ],
  }),
  doSubmit(mode) {
    const modelValue = {
      ...model.value,
      linux_path: linuxPath.value, // 提交时使用计算后的 linuxPath
    };
    return (mode === 'create'
      ? storageUsageApi.create(modelValue)
      : storageUsageApi.replace(modelValue.id, modelValue));
  },
  onSuccess(mode) {
    ElMessage.success(`${mode === 'create' ? '新增' : '修改'}成功`);
    emit('submitted');
    close();
  },
});

const groupName = ref('');
const userName = ref('');

const linuxPath = computed(() => {
  if (mode.value === 'create') {
    return `${groupName.value}/${userName.value}`;
  }
  return model.value.linux_path;
});

const getGroupName = async (groupId) => {
  if (groupId) {
    try {
      const group = await groupApi.fetchById(groupId);
      groupName.value = group.linux_path;
    } catch (error) {
      console.error('Failed to fetch group details:', error);
    }
  } else {
    groupName.value = '';
  }
};

const getUserName = async (userId) => {
  if (userId) {
    try {
      const user = await userApi.fetchById(userId);
      userName.value = user.rd_username;
    } catch (error) {
      console.error('Failed to fetch user details:', error);
    }
  } else {
    userName.value = '';
  }
};

const handleGroupChange = (groupId) => {
  model.value.group_id = groupId;
  getGroupName(groupId);
};

const handleUserChange = (userId) => {
  model.value.user_id = userId;
  getUserName(userId);
};

defineExpose({
  edit(existing) {
    if (existing) {
      edit({
        ...existing,
      });
      getGroupName(existing.group_id);
      getUserName(existing.user_id);
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
    :title="mode === 'create' ? '新增用户目录' : '修改用户目录'"
    @close="formRef.clearValidate()">
    <ElForm
      ref="formRef"
      label-width="auto"
      :model="model"
      :rules="modelRules"
    >
      <ElFormItem
        label="关联项目组"
        prop="group_id">
        <GroupSelect
          v-model="model.group_id"
          :multiple="false"
          @change="handleGroupChange" />
      </ElFormItem>
      <ElFormItem
        label="关联研发用户"
        prop="user_id">
        <RdUserSelect
          v-model="model.user_id"
          :multiple="false"
          @change="handleUserChange" />
      </ElFormItem>
      <ElFormItem
        label="存储集群"
        prop="storage_cluster_id">
        <StorageClusterSelect
          v-model="model.storage_cluster_id"
          :multiple="false"
          :clearable="true" />
      </ElFormItem>
      <ElFormItem label="Linux路径">
        <ElInput
          v-model="linuxPath"
          :disabled="true" />
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
