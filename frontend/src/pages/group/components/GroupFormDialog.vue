<script setup>
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElMessage,ElInputNumber,ElDatePicker,ElSwitch,ElTooltip } from 'element-plus';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import groupApi from '@/api/group-api';
import ProjectSelect from '@/components/form/ProjectSelect.vue'
import QtreeSelect from '@/components/form/QtreeSelect.vue'
import StorageClusterSelect from '@/components/form/StorageClusterSelect.vue'
import MailSelect from '@/components/form/MailSelect.vue'
import RdUserSelect from '@/components/form/RdUserSelect.vue'
import HostSelect from '@/components/form/HostsSelect.vue'
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
  project_id:null,
  qtree_id: null,
  linux_path:null,
  back_path:null,
  enable_monitoring:true,
  associate_multiple_groups:false,
  in_charge_user_id:null,
  monitor_host_id:null,
  associated_mail_groups:[]
}), {
  rules: (model) => ({
    name: [
      { type: 'string', required: true, message: '名称不能为空', trigger: 'blur' },
    ],
    project_id: [
      { type: 'number', required: true, message: '关联项目不能为空', trigger: 'blur' },
    ],
    qtree_id: [
      { type: 'number', required: true, message: '关联Qtree不能为空', trigger: 'blur' },
    ],
    linux_path: [
      { type: 'string', required: true, message: '关联linux路径不能为空', trigger: 'blur' },
    ],
    // monitor_host_id: [
    //   { type: 'number', required: true, message: '关联主机不能为空', trigger: 'blur' },
    // ],
    // in_charge_user_id: [
    //   { type: 'number', required: true, message: '项目组开发代表不能为空', trigger: 'blur' },
    // ],
  }),
  doSubmit(mode) {
      const modelValue = {
        ...model.value,
      };
      return (mode === 'create'
        ? groupApi.create(modelValue)
        : groupApi.replace(modelValue.id, modelValue))
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
          v-model="model.project_id"
          :multiple="false" />
      </ElFormItem>
      <ElFormItem
        label="关联Qtree"
        prop="qtree_id">
        <QtreeSelect
          v-model="model.qtree_id"
          :multiple="false" />
      </ElFormItem>
      <ElFormItem
        label="存储集群"
        prop="storage_cluster_id">
        <StorageClusterSelect
          v-model="model.storage_cluster_id"
          :multiple="false"
          :clearable="true" />
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
