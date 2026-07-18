<script setup>
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElMessage } from 'element-plus';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import groupApi from '@/api/group-api';
import userApi from '@/api/users-api';
import storageUsageApi from '@/api/storage-usage-api';
import GroupSelect from '@/components/form/GroupSelect.vue';
import RdUserSelect from '@/components/form/RdUserSelect.vue';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import { ref, computed } from 'vue';

const number = 'number';
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
  group_id: null,
  user_id: null,
  project_id: null,
  linux_path: '',
}), {
  rules: (model) => ({
    project_id: [
      { type: number, required: true, message: '项目不能为空', trigger: 'blur' },
    ],
    group_id: [
      { type: number, required: true, message: '关联项目组不能为空', trigger: 'blur' },
    ],
    user_id: [
      { type: number, required: true, message: '关联用户不能为空', trigger: 'blur' },
    ],
  }),
  doSubmit(mode) {
    const modelValue = {
      group_id: model.value.group_id,
      user_id: model.value.user_id,
    };
    return (mode === 'create'
      ? storageUsageApi.create(modelValue)
      : storageUsageApi.replace(model.value.id, modelValue));
  },
  onSuccess(mode) {
    ElMessage.success(`${mode === 'create' ? '新增' : '修改'}成功`);
    emit('submitted');
    forceClose();
  },
});

const groupName = ref('');
const userName = ref('');
const selectedGroup = ref(null);

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
      if (model.value.project_id && group.project?.id !== model.value.project_id) {
        model.value.group_id = null;
        groupName.value = '';
        selectedGroup.value = null;
        ElMessage.error('所选项目组不属于当前项目');
        return;
      }
      groupName.value = group.linux_path;
      selectedGroup.value = group;
    } catch (error) {
      console.error('Failed to fetch group details:', error);
    }
  } else {
    groupName.value = '';
    selectedGroup.value = null;
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

const handleProjectChange = (projectId) => {
  model.value.project_id = projectId;
  model.value.group_id = null;
  groupName.value = '';
  selectedGroup.value = null;
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
        project_id: existing.project?.id ?? existing.project_id,
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
    class="write-form-dialog"
    :title="mode === 'create' ? '新增用户目录' : '修改用户目录'"
    :before-close="beforeClose"
    @close="formRef.clearValidate()">
    <template #header>
      <div class="write-form-dialog__heading">
        <h2>{{ mode === 'create' ? '新增用户目录' : '修改用户目录' }}</h2>
      </div>
    </template>
    <ElForm
      ref="formRef"
      class="write-form write-form-grid"
      label-position="top"
      :model="model"
      :rules="modelRules"
    >
      <div class="write-form-section">归属关系</div>
      <ElFormItem label="项目">
        <ProjectSelect
          :model-value="model.project_id"
          :multiple="false"
          :clearable="true"
          @update:model-value="handleProjectChange" />
      </ElFormItem>
      <ElFormItem
        label="关联项目组"
        prop="group_id">
        <GroupSelect
          v-model="model.group_id"
          :project-id="model.project_id"
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
      <ElFormItem label="存储集群">
        <span data-test="derived-storage-cluster">
          {{ selectedGroup?.storage_cluster?.name || '-' }}
        </span>
      </ElFormItem>
      <div class="write-form-section">路径预览</div>
      <ElFormItem
        class="write-form-field--full"
        label="Linux路径">
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
        {{ submitting ? (mode === 'create' ? '创建中…' : '保存中…') : (mode === 'create' ? '创建目录' : '保存修改') }}
      </ElButton>
    </template>
  </ElDialog>
</template>
