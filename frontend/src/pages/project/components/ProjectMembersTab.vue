<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';
import membershipApi from '@/api/project-membership-api.js';
import RdUserSelect from '@/components/form/RdUserSelect.vue';

const props = defineProps({
  projectId: {
    type: Number,
    required: true,
  },
  canManageProjectAdmins: Boolean,
});

const members = ref([]);
const loading = ref(false);
const dialogVisible = ref(false);
const submitting = ref(false);
const editingUserId = ref(null);
const form = reactive({ user_id: null, role: 'reader' });
const roleOptions = computed(() => {
  const options = [
    { value: 'reader', label: '只读成员' },
    { value: 'editor', label: '编辑成员' },
  ];
  if (props.canManageProjectAdmins) options.push({ value: 'project_admin', label: '项目管理员' });
  return options;
});

function canManage(member) {
  return member.role !== 'project_admin' || props.canManageProjectAdmins;
}

async function loadMembers() {
  loading.value = true;
  try {
    members.value = await membershipApi.list(props.projectId);
  } catch {
    members.value = [];
    ElMessage.error('加载项目成员失败，请稍后重试');
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingUserId.value = null;
  form.user_id = null;
  form.role = 'reader';
  dialogVisible.value = true;
}

function openEdit(member) {
  editingUserId.value = member.user_id;
  form.user_id = member.user_id;
  form.role = member.role;
  dialogVisible.value = true;
}

async function submit() {
  if (!form.user_id) {
    ElMessage.warning('请选择用户');
    return;
  }
  submitting.value = true;
  try {
    if (editingUserId.value == null) {
      await membershipApi.create(props.projectId, { user_id: form.user_id, role: form.role });
    } else {
      await membershipApi.update(props.projectId, editingUserId.value, { role: form.role });
    }
    dialogVisible.value = false;
    ElMessage.success(editingUserId.value == null ? '项目成员已添加' : '项目成员角色已更新');
    await loadMembers();
  } finally {
    submitting.value = false;
  }
}

function confirmRemove(member) {
  ElMessageBox.confirm(`确认移除项目成员「${member.user?.rd_username || member.user_id}」？`, '移除项目成员', {
    type: 'warning',
    confirmButtonText: '移除成员',
    cancelButtonText: '取消',
  }).then(async () => {
    await membershipApi.remove(props.projectId, member.user_id);
    ElMessage.success('项目成员已移除');
    await loadMembers();
  }).catch(() => {});
}

onMounted(loadMembers);
</script>

<template>
  <section class="project-members-tab">
    <div class="section-toolbar">
      <div>
        <h3>项目成员</h3>
        <p>管理本项目的只读和编辑成员。</p>
      </div>
      <ElButton
        type="primary"
        @click="openCreate"><i class="i-ri-user-add-line"></i>添加成员</ElButton>
    </div>
    <ElTable
      v-loading="loading"
      :data="members">
      <ElTableColumn
        label="用户"
        min-width="180">
        <template #default="{ row }">{{ row.user?.rd_username || row.user?.username || row.user_id }}</template>
      </ElTableColumn>
      <ElTableColumn
        prop="role"
        label="项目角色"
        min-width="130">
        <template #default="{ row }"><ElTag>{{ row.role }}</ElTag></template>
      </ElTableColumn>
      <ElTableColumn
        prop="updated_at"
        label="更新时间"
        min-width="176" />
      <ElTableColumn
        align="right"
        width="150"
        fixed="right">
        <template #default="{ row }">
          <div
            v-if="canManage(row)"
            class="list-row-actions">
            <ElButton
              size="small"
              plain
              @click="openEdit(row)">编辑</ElButton>
            <ElButton
              size="small"
              plain
              type="danger"
              @click="confirmRemove(row)">移除</ElButton>
          </div>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDialog
      v-model="dialogVisible"
      class="write-form-dialog write-form-dialog--compact"
      :title="editingUserId == null ? '添加项目成员' : '编辑项目成员'">
      <ElForm
        class="write-form write-form-grid write-form-grid--single"
        :model="form"
        label-position="top">
        <ElFormItem
          label="用户"
          required>
          <RdUserSelect
            v-model="form.user_id"
            :disabled="editingUserId != null"
            clearable />
        </ElFormItem>
        <ElFormItem
          label="项目角色"
          required>
          <ElSelect v-model="form.role">
            <ElOption
              v-for="option in roleOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton
          :disabled="submitting"
          @click="dialogVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="submitting"
          @click="submit">保存</ElButton>
      </template>
    </ElDialog>
  </section>
</template>

<style scoped>
.section-toolbar { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--spacing-md); margin-bottom: var(--spacing-md); }
.section-toolbar h3 { margin: 0 0 4px; color: var(--text-primary); font-size: var(--font-size-lg); }
.section-toolbar p { margin: 0; color: var(--text-secondary); font-size: var(--font-size-sm); }
.section-toolbar i { margin-right: var(--spacing-xs); }
</style>
