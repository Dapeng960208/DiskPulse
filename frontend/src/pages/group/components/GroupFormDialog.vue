<script setup>
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElSwitch,
} from 'element-plus';
import { computed, ref } from 'vue';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import groupApi from '@/api/group-api';
import MailSelect from '@/components/form/MailSelect.vue';
import ProjectSelect from '@/components/form/ProjectSelect.vue';
import QtreeSelect from '@/components/form/QtreeSelect.vue';
import RdUserSelect from '@/components/form/RdUserSelect.vue';
import VolumeSelect from '@/components/form/VolumeSelect.vue';

const emit = defineEmits(['submitted']);
const { visible, open, close } = useDialog();
const environmentOptions = ref([]);
const loadingEnvironments = ref(false);

function initialModel() {
  return {
    name: '',
    project_id: null,
    project_environment_id: null,
    target_type: null,
    volume_id: null,
    qtree_id: null,
    linux_path: null,
    back_path: null,
    enable_monitoring: true,
    associate_multiple_groups: false,
    in_charge_user_id: null,
    monitor_host_id: null,
    associated_mail_groups: [],
  };
}

const {
  formRef,
  mode,
  model,
  modelRules,
  submitting,
  edit: editForm,
  submit,
} = useForm(initialModel, {
  rules: (currentModel) => ({
    name: [
      { type: 'string', required: true, message: '名称不能为空', trigger: 'blur' },
    ],
    project_id: [
      { type: 'number', required: true, message: '关联项目不能为空', trigger: 'change' },
    ],
    project_environment_id: [
      { type: 'number', required: true, message: '存储环境不能为空', trigger: 'change' },
    ],
    target_type: [
      { type: 'string', required: true, message: '目标类型不能为空', trigger: 'change' },
    ],
    ...(currentModel.value.target_type === 'volume' ? {
      volume_id: [
        { type: 'number', required: true, message: 'Volume不能为空', trigger: 'change' },
      ],
    } : {
      qtree_id: [
        { type: 'number', required: true, message: 'Qtree不能为空', trigger: 'change' },
      ],
    }),
    linux_path: [
      { type: 'string', required: true, message: '关联linux路径不能为空', trigger: 'blur' },
    ],
  }),
  doSubmit(currentMode) {
    const payload = buildPayload();
    return currentMode === 'create'
      ? groupApi.create(payload)
      : groupApi.replace(model.value.id, payload);
  },
  onSuccess(currentMode) {
    ElMessage.success(`${currentMode === 'create' ? '新增' : '修改'}成功`);
    emit('submitted');
    close();
  },
  onFailure() {
    ElMessage.error('保存项目组失败，请稍后重试');
  },
});

const selectedEnvironment = computed(() => environmentOptions.value.find(
  (environment) => environment.id === model.value.project_environment_id,
));

async function loadEnvironments(projectId) {
  environmentOptions.value = [];
  if (!projectId) return;
  loadingEnvironments.value = true;
  try {
    const { default: environmentApi } = await import(
      '@/api/project-storage-environment-api'
    );
    const response = await environmentApi.fetchByProject(projectId, {
      page: 1,
      size: 100,
    });
    environmentOptions.value = response.content;
  } catch {
    environmentOptions.value = [];
    ElMessage.error?.('加载项目存储环境失败，请稍后重试');
  } finally {
    loadingEnvironments.value = false;
  }
}

async function changeProject(projectId) {
  model.value.project_id = projectId;
  model.value.project_environment_id = null;
  model.value.target_type = null;
  model.value.volume_id = null;
  model.value.qtree_id = null;
  await loadEnvironments(projectId);
}

function changeEnvironment(environmentId) {
  model.value.project_environment_id = environmentId;
  model.value.volume_id = null;
  model.value.qtree_id = null;
  model.value.target_type = selectedEnvironment.value?.storage_cluster?.storage_type === 'isilon'
    ? 'volume'
    : null;
}

function changeTargetType(targetType) {
  model.value.target_type = targetType;
  model.value.volume_id = null;
  model.value.qtree_id = null;
}

function buildPayload() {
  const payload = {};
  [
    'name',
    'linux_path',
    'back_path',
    'enable_monitoring',
    'associate_multiple_groups',
    'in_charge_user_id',
    'monitor_host_id',
    'associated_mail_groups',
    'completed',
    'back_up_enabled',
  ].forEach((field) => {
    if (model.value[field] !== undefined) payload[field] = model.value[field];
  });
  payload.project_environment_id = model.value.project_environment_id;
  if (model.value.target_type === 'volume' && model.value.volume_id != null) {
    payload.volume_id = model.value.volume_id;
  } else if (model.value.target_type === 'qtree' && model.value.qtree_id != null) {
    payload.qtree_id = model.value.qtree_id;
  } else if (model.value.target_type == null && model.value.volume_id != null) {
    payload.volume_id = model.value.volume_id;
  } else if (model.value.target_type == null && model.value.qtree_id != null) {
    payload.qtree_id = model.value.qtree_id;
  }
  return payload;
}

defineExpose({
  edit(existing) {
    if (!existing) {
      environmentOptions.value = [];
      editForm();
      open();
      return;
    }

    const normalized = {
      ...initialModel(),
      ...existing,
      project_id: existing.project_id ?? existing.project?.id ?? null,
      project_environment_id: existing.project_environment_id
        ?? existing.project_environment?.id
        ?? null,
      target_type: existing.storage_target?.type
        ?? (existing.volume_id != null ? 'volume' : 'qtree'),
      volume_id: existing.volume_id
        ?? (existing.storage_target?.type === 'volume' ? existing.storage_target.id : null),
      qtree_id: existing.qtree_id
        ?? (existing.storage_target?.type === 'qtree' ? existing.storage_target.id : null),
    };
    editForm(normalized);
    environmentOptions.value = existing.project_environment ? [{
      ...existing.project_environment,
      storage_cluster: existing.storage_cluster,
    }] : [];
    open();
    if (normalized.project_id) loadEnvironments(normalized.project_id);
  },
});
</script>

<template>
  <ElDialog
    v-model="visible"
    :title="mode === 'create' ? '新增项目组监控配置' : '修改项目组监控配置'"
    @close="formRef.clearValidate()">
    <ElForm
      ref="formRef"
      label-width="auto"
      :model="model"
      :rules="modelRules"
    >
      <ElFormItem
        label="组名"
        prop="name">
        <ElInput v-model="model.name"></ElInput>
      </ElFormItem>
      <ElFormItem
        label="关联项目"
        prop="project_id">
        <ProjectSelect
          :model-value="model.project_id"
          :multiple="false"
          @update:model-value="changeProject" />
      </ElFormItem>
      <ElFormItem
        label="存储环境"
        prop="project_environment_id">
        <ElSelect
          data-test="project-environment-select"
          :model-value="model.project_environment_id"
          :loading="loadingEnvironments"
          placeholder="请选择存储环境"
          @update:model-value="changeEnvironment">
          <ElOption
            v-for="environment in environmentOptions"
            :key="environment.id"
            :label="environment.name"
            :value="environment.id" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem
        v-if="selectedEnvironment"
        label="存储集群">
        <span>
          {{ selectedEnvironment.storage_cluster?.name }}
          / {{ selectedEnvironment.storage_cluster?.storage_type }}
        </span>
      </ElFormItem>
      <ElFormItem
        v-if="selectedEnvironment?.storage_cluster?.storage_type === 'netapp'"
        label="目标类型"
        prop="target_type">
        <ElSelect
          data-test="storage-target-type"
          :model-value="model.target_type"
          placeholder="请选择目标类型"
          @update:model-value="changeTargetType">
          <ElOption
            label="Volume"
            value="volume" />
          <ElOption
            label="Qtree"
            value="qtree" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem
        v-else-if="selectedEnvironment"
        label="目标类型">
        Volume
      </ElFormItem>
      <ElFormItem
        v-if="selectedEnvironment && model.target_type === 'volume'"
        label="Volume"
        prop="volume_id">
        <VolumeSelect
          v-model="model.volume_id"
          :storage-cluster-id="selectedEnvironment.storage_cluster?.id"
          :multiple="false" />
      </ElFormItem>
      <ElFormItem
        v-if="selectedEnvironment && model.target_type === 'qtree'"
        label="Qtree"
        prop="qtree_id">
        <QtreeSelect
          v-model="model.qtree_id"
          :storage-cluster-id="selectedEnvironment.storage_cluster?.id"
          :multiple="false" />
      </ElFormItem>
      <!-- <ElFormItem
        label="关联公共主机"
        prop="monitor_host_id">
        <HostSelect v-model="model.monitor_host_id"></HostSelect>
      </ElFormItem> -->
      <ElFormItem
        label="关联Linux路径"
        prop="linux_path">
        <ElInput v-model="model.linux_path"></ElInput>
      </ElFormItem>
      <!-- <ElFormItem label="备份路径">
      <ElInput v-model="model.back_path"></ElInput>
    </ElFormItem> -->
      <ElFormItem label="是否单个volume关联多个项目组">
        <ElSwitch v-model="model.associate_multiple_groups"></ElSwitch>
      </ElFormItem>
      <ElFormItem
        label="项目组开发代表"
        prop="in_charge_user_id">
        <RdUserSelect
          v-model="model.in_charge_user_id"
          :multiple="false"
          :clearable="true" />
      </ElFormItem>
      <ElFormItem label="关联群组/个人邮箱">
        <MailSelect
          v-model="model.associated_mail_groups"
          :type="'distribution'"
          :multiple="true" />
      </ElFormItem>
      <ElFormItem label="是否监控">
        <ElSwitch v-model="model.enable_monitoring"></ElSwitch>
      </ElFormItem>
      <ElFormItem label="是否已结项">
        <ElSwitch v-model="model.completed"></ElSwitch>
      </ElFormItem>
      <ElFormItem label="是否开启离职数据备份">
        <ElSwitch v-model="model.back_up_enabled"></ElSwitch>
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
