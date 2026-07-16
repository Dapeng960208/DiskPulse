<script setup>
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElInputNumber, ElMessage, ElOption, ElSelect, ElSwitch } from 'element-plus';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import storageClusterApi from '@/api/storage-cluster-api';
import { ref, watch } from 'vue';

const emit = defineEmits(['submitted']);
const isilonAccountHelpVisible = ref(false);
const isilonAccountCommands = `ROLE='DiskPulseMonitor'
SVC_USER='diskpulse_monitor'

isi auth roles view "$ROLE" --zone System >/dev/null 2>&1 ||
isi auth roles create "$ROLE" --zone System --description "DiskPulse read-only monitoring"

isi auth users create "$SVC_USER" --zone System --enabled yes --password-expires no --set-password
isi auth roles modify "$ROLE" --zone System --add-user "$SVC_USER"

isi auth roles modify "$ROLE" --zone System \\
  --add-priv-read ISI_PRIV_LOGIN_PAPI \\
  --add-priv-read ISI_PRIV_CLUSTER \\
  --add-priv-read ISI_PRIV_SMARTPOOLS \\
  --add-priv-read ISI_PRIV_QUOTA \\
  --add-priv-read ISI_PRIV_STATISTICS \\
  --add-priv-read ISI_PRIV_EVENT \\
  --add-priv-read ISI_PRIV_SYS_TIME

isi auth users view "$SVC_USER" --zone System
isi auth roles view "$ROLE" --zone System`;

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
    forceClose();
  },
});

watch(() => model.value.protocol, (protocol) => {
  if (protocol === 'http') model.value.tls_verify = false;
});

watch(() => model.value.storage_type, (storageType) => {
  if (storageType !== 'isilon') {
    isilonAccountHelpVisible.value = false;
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
    class="write-form-dialog"
    :title="mode === 'create' ? '新增存储集群' : '编辑存储集群'"
    :before-close="beforeClose"
    @close="formRef.clearValidate()">
    <template #header>
      <div class="write-form-dialog__heading">
        <h2>{{ mode === 'create' ? '新增存储集群' : '编辑存储集群' }}</h2>
        <p>配置设备连接、安全校验和采集状态。</p>
      </div>
    </template>
    <ElForm
      ref="formRef"
      class="write-form write-form-grid"
      label-position="top"
      :model="model"
      :rules="modelRules"
    >
      <div class="write-form-section">基本信息</div>
      <ElFormItem
        label="集群名称"
        prop="name">
        <ElInput
          v-model="model.name"
          clearable
          placeholder="请输入集群名称" />
      </ElFormItem>
      <ElFormItem
        class="write-form-field--full"
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
      <div class="write-form-section">连接配置</div>
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
      <div
        v-if="model.storage_type === 'isilon'"
        class="write-form-section">Isilon Session</div>
      <ElFormItem
        v-if="model.storage_type === 'isilon'"
        class="write-form-field--full"
        label="账号要求">
        <div class="account-help-trigger">
          <ElButton
            data-test="isilon-account-help-trigger"
            link
            type="primary"
            @click="isilonAccountHelpVisible = true">
            查看账号创建与最小权限配置
          </ElButton>
          <span>必须使用 OneFS 本地服务账号</span>
        </div>
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
      <div class="write-form-section">状态</div>
      <ElFormItem
        class="write-form-field--full"
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
        {{ submitting ? (mode === 'create' ? '创建中…' : '保存中…') : (mode === 'create' ? '创建集群' : '保存修改') }}
      </ElButton>
    </template>
  </ElDialog>
  <ElDialog
    v-if="model.storage_type === 'isilon'"
    v-model="isilonAccountHelpVisible"
    data-test="isilon-account-help-dialog"
    title="Isilon 采集账号与权限要求"
    width="min(720px, 92vw)"
    append-to-body>
    <div class="account-help">
      <h3>账号要求</h3>
      <ul>
        <li>使用 System Zone 的 OneFS 本地服务账号，不使用 NIS、LDAP 或 AD 人员账号。</li>
        <li>账号只加入 <code>DiskPulseMonitor</code> 只读角色，不授予系统管理权限。</li>
        <li>推荐使用 HTTPS，并将 Session 缓存选择为“不缓存（每次安全注销）”。</li>
      </ul>

      <h3>root 创建与授权命令</h3>
      <p>在任一 Isilon 节点使用 root 执行；创建用户时按提示输入密码。</p>
      <pre>{{ isilonAccountCommands }}</pre>

      <h3>DiskPulse 配置</h3>
      <ol>
        <li>API 用户名填写 <code>diskpulse_monitor</code>，密码填写创建时设置的密码。</li>
        <li>API 端口通常为 <code>8080</code>，协议选择 HTTPS。</li>
        <li>保存后重启 Celery Worker，使采集任务加载新账号。</li>
      </ol>
    </div>
    <template #footer>
      <ElButton @click="isilonAccountHelpVisible = false">
        关闭
      </ElButton>
    </template>
  </ElDialog>
</template>

<style scoped>
:deep(.el-form-item) {
  margin-bottom: 20px;
}

.account-help-trigger {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.account-help {
  color: var(--el-text-color-regular);
  line-height: 1.65;
}

.account-help h3 {
  margin: 18px 0 8px;
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.account-help h3:first-child {
  margin-top: 0;
}

.account-help ul,
.account-help ol {
  margin: 0;
  padding-left: 22px;
}

.account-help p {
  margin: 0 0 10px;
}

.account-help pre {
  max-height: 340px;
  margin: 0;
  padding: 14px 16px;
  overflow: auto;
  border: 1px solid var(--el-border-color-light);
  border-radius: 4px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  font: 12px/1.65 monospace;
  white-space: pre-wrap;
  word-break: break-word;
  user-select: text;
}
</style>
