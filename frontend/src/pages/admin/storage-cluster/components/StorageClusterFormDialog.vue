<script setup>
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElInputNumber, ElMessage, ElOption, ElSelect, ElSwitch } from 'element-plus';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import storageClusterApi from '@/api/storage-cluster-api';
import { watch } from 'vue';

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
  name: '',
  description: '',
  storage_type: null,
  storage_host: '',
  storage_port: 22,
  storage_user: '',
  storage_password: '',
  isilon_session_cache_mode: 'none',
  isilon_session_cache_path: null,
  protocol: 'https',
  tls_verify: true,
  is_active: true,
}), {
  rules: () => ({
    name: [
      { type: 'string', required: true, message: '集群名称不能为空', trigger: 'blur' },
    ],
    storage_type: [
      { type: 'string', required: true, message: '存储类型不能为空', trigger: 'change' },
    ],
    storage_host: [
      { type: 'string', required: true, message: '主机地址不能为空', trigger: 'blur' },
    ],
    storage_port: [
      { required: true, message: '端口不能为空', trigger: 'blur' },
    ],
    storage_user: [
      { type: 'string', required: true, message: '用户名不能为空', trigger: 'blur' },
    ],
  }),
  doSubmit(mode) {
    const modelValue = {
      ...model.value,
      tls_verify: model.value.protocol === 'https' && model.value.tls_verify,
      isilon_session_cache_mode: model.value.storage_type === 'isilon'
        ? model.value.isilon_session_cache_mode
        : 'none',
      isilon_session_cache_path: model.value.storage_type === 'isilon'
        && model.value.isilon_session_cache_mode === 'file'
        ? model.value.isilon_session_cache_path || '.isilon_cache/cache.json'
        : null,
    };
    return mode === 'create'
      ? storageClusterApi.create(modelValue)
      : storageClusterApi.replace(modelValue.id, modelValue);
  },
  onSuccess(mode) {
    ElMessage.success(`${mode === 'create' ? '新增' : '修改'}成功`);
    emit('submitted');
    close();
  },
});

watch(() => model.value.protocol, (protocol) => {
  if (protocol === 'http') model.value.tls_verify = false;
});

watch(() => model.value.storage_type, (storageType) => {
  if (storageType !== 'isilon') {
    model.value.isilon_session_cache_mode = 'none';
    model.value.isilon_session_cache_path = null;
  }
});

watch(() => model.value.isilon_session_cache_mode, (cacheMode) => {
  model.value.isilon_session_cache_path = cacheMode === 'file'
    ? model.value.isilon_session_cache_path || '.isilon_cache/cache.json'
    : null;
});

defineExpose({
  edit(existing) {
    if (existing) {
      edit({ ...existing });
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
    :title="mode === 'create' ? '新增存储集群' : '编辑存储集群'"
    @close="formRef.clearValidate()">
    <ElForm
      ref="formRef"
      label-width="100"
      :model="model"
      :rules="modelRules"
    >
      <ElFormItem
        label="集群名称"
        prop="name">
        <ElInput
          v-model="model.name"
          clearable
          placeholder="请输入集群名称" />
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
        label="存储类型"
        prop="storage_type">
        <ElSelect
          v-model="model.storage_type"
          placeholder="请选择存储类型">
          <ElOption
            label="NetApp"
            value="netapp" />
          <ElOption
            label="Isilon"
            value="isilon" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem
        label="主机地址"
        prop="storage_host">
        <ElInput
          v-model="model.storage_host"
          clearable
          placeholder="请输入主机地址" />
      </ElFormItem>
      <ElFormItem
        label="访问协议"
        prop="protocol">
        <ElSelect v-model="model.protocol">
          <ElOption
            label="HTTPS"
            value="https" />
          <ElOption
            label="HTTP"
            value="http" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem
        label="TLS 证书校验"
        prop="tls_verify">
        <ElSwitch
          v-model="model.tls_verify"
          :disabled="model.protocol === 'http'"
          active-text="校验"
          inactive-text="不校验" />
      </ElFormItem>
      <ElFormItem
        label="API 端口"
        prop="storage_port">
        <ElInputNumber
          v-model="model.storage_port"
          :min="1"
          :max="65535"
          controls-position="right"
          style="width: 100%" />
      </ElFormItem>
      <ElFormItem
        label="API 用户名"
        prop="storage_user">
        <ElInput
          v-model="model.storage_user"
          clearable
          placeholder="请输入 API 用户名" />
      </ElFormItem>
      <ElFormItem
        label="API 密码"
        prop="storage_password">
        <ElInput
          v-model="model.storage_password"
          type="password"
          show-password
          clearable
          placeholder="请输入 API 密码" />
      </ElFormItem>
      <ElFormItem
        v-if="model.storage_type === 'isilon'"
        data-test="isilon-session-cache-mode"
        label="Session 缓存"
        prop="isilon_session_cache_mode">
        <ElSelect v-model="model.isilon_session_cache_mode">
          <ElOption
            label="不缓存（每次安全注销）"
            value="none" />
          <ElOption
            label="本地文件"
            value="file" />
          <ElOption
            label="Redis"
            value="redis" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem
        v-if="model.storage_type === 'isilon' && model.isilon_session_cache_mode === 'file'"
        data-test="isilon-session-cache-path"
        label="缓存文件"
        prop="isilon_session_cache_path">
        <ElInput
          v-model="model.isilon_session_cache_path"
          clearable
          placeholder="请输入服务端缓存文件路径" />
      </ElFormItem>
      <ElFormItem
        label="是否启用"
        prop="is_active">
        <ElSwitch
          v-model="model.is_active"
          active-text="启用"
          inactive-text="停用" />
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

<style scoped>
:deep(.el-form-item) {
  margin-bottom: 20px;
}
</style>
