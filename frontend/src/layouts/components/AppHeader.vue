<script setup>
import { ref } from 'vue';
import { ElButton, ElDialog, ElDropdown, ElDropdownItem, ElDropdownMenu, ElHeader, ElMessage, ElMessageBox, ElOption, ElSelect, ElSpace } from 'element-plus';
import { useCurrentUser } from '@/stores/current-user';
import { isAuthenticated, removeToken } from '@/utils/authorization';
import usersApi from '@/api/users-api';
import { toLoginPage } from '@/utils';
import { getDefaultAvatar } from '@/utils/default-avatar';
import UserAvatar from '@/components/data/UserAvatar.vue';
import ThemeSwitch from '@/components/basic/ThemeSwitch.vue';
import logo from '@/assets/logo.png';
defineProps({
  height: {
    type: String,
    default: '60px',
  },
});
const title = import.meta.env.VITE_APP_TITLE;
const currentUser = useCurrentUser();
const timeZoneDialogVisible = ref(false);
const timeZoneDraft = ref('Asia/Shanghai');
const timeZones = ref([]);
const savingTimeZone = ref(false);

async function openTimeZoneSettings() {
  const { result } = await usersApi.fetchTimeZones();
  timeZones.value = result;
  timeZoneDraft.value = currentUser.timeZone;
  timeZoneDialogVisible.value = true;
}

async function saveTimeZone() {
  savingTimeZone.value = true;
  try {
    const { result } = await usersApi.updateCurrentProfile({ time_zone: timeZoneDraft.value });
    currentUser.setCurrentUser(result);
    timeZoneDialogVisible.value = false;
    ElMessage.success('时区已更新');
  } finally {
    savingTimeZone.value = false;
  }
}

function handleMenuClick(command) {
  if (command === 'logout') {
    ElMessageBox.confirm('确认退出登录？', '提示', {
      type: 'warning',
      confirmButtonText: '退出登录',
      cancelButtonText: '我再想想',
    }).then(() => usersApi.logout().then(() => {
      removeToken();
      currentUser.$reset();
      toLoginPage();
    })).catch(() => {});
  } else if (command === 'time-zone') {
    openTimeZoneSettings().catch(() => ElMessage.error('时区列表加载失败'));
  }
}
</script>

<template>
  <ElHeader class="app-header">
    <div class="app-header__content">
      <RouterLink
        class="app-header__brand"
        to="/">
        <div class="brand-content">
          <img
            class="brand-logo"
            :src="logo"
            alt="Logo">
        </div>
      </RouterLink>
      <span class="brand-title">{{ title }}</span>

      <div class="app-header__actions">
        <div class="header-action-item">
          <ThemeSwitch />
        </div>

        <ElDropdown
          v-if="isAuthenticated()"
          class="user-dropdown"
          trigger="click"
          placement="bottom-end"
          @command="handleMenuClick"
        >
          <div class="user-info">
            <UserAvatar
              class="user-avatar"
              :src="currentUser.avatarUrl || getDefaultAvatar(currentUser.username || currentUser.displayName)" />
            <span class="user-name">{{ currentUser.displayName }}</span>
            <i class="dropdown-icon i-ri-arrow-down-s-fill"></i>
          </div>
          <template #dropdown>
            <ElDropdownMenu class="user-dropdown-menu">
              <ElDropdownItem command="time-zone">
                <i class="i-ri-time-zone-line"></i>
                <span>时区设置</span>
              </ElDropdownItem>
              <ElDropdownItem
                class="logout-item"
                command="logout">
                <i class="i-ri-logout-box-r-line"></i>
                <span>退出登录</span>
              </ElDropdownItem>
            </ElDropdownMenu>
          </template>
        </ElDropdown>

        <ElButton
          v-else
          type="primary"
          @click="toLoginPage">
          登录
        </ElButton>

        <ElDialog
          v-model="timeZoneDialogVisible"
          title="时区设置"
          width="min(92vw, 420px)">
          <p class="time-zone-description">网页时间和手动导出将按此 IANA 时区展示。</p>
          <ElSelect
            v-model="timeZoneDraft"
            filterable
            placeholder="搜索时区"
            style="width: 100%">
            <ElOption
              v-for="timeZone in timeZones"
              :key="timeZone"
              :label="timeZone"
              :value="timeZone" />
          </ElSelect>
          <template #footer>
            <ElButton @click="timeZoneDialogVisible = false">取消</ElButton>
            <ElButton
              type="primary"
              :loading="savingTimeZone"
              @click="saveTimeZone">保存</ElButton>
          </template>
        </ElDialog>
      </div>
    </div>
  </ElHeader>
</template>

<style lang="scss">
// 覆盖 ElHeader 默认的 padding（非 scoped，确保能覆盖组件库样式）
.app-header.el-header {
  padding: 0 !important;
}
</style>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';

.app-header {
  height: v-bind(height);
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  position: relative;
  z-index: var(--z-sticky);

  // 背景模糊效果
  @include backdrop-blur;

  .app-header__content {
    display: flex;
    align-items: center;
    height: 100%;
    padding: 0;
    width: 100%;
  }

  .app-header__brand {
    // 与左侧菜单栏宽度保持一致
    width: 240px;
    min-width: 240px;
    flex-shrink: 0;
    color: inherit;
    text-decoration: none;
    transition: var(--transition-base);
    padding: 0 var(--spacing-lg);
    height: 100%;
    display: flex;
    align-items: center;
    border-right: 1px solid var(--border-color);
    box-sizing: border-box;

    &:hover {
      opacity: 0.8;
    }

    .brand-content {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
    }

    .brand-logo {
      display: block;
      flex-shrink: 0;
      transition: var(--transition-base);
      max-width: 100%;
      max-height: 40px;
      width: auto;
      height: auto;
      object-fit: contain;

      &:hover {
        transform: scale(1.05);
      }
    }
  }

  // divider 和 title 在 brand 区域外面
  .brand-divider {
    width: 1px;
    height: 20px;
    background: var(--border-color);
    flex-shrink: 0;
    margin: 0 var(--spacing-md);
  }

  .brand-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    white-space: nowrap;
    flex-shrink: 0;
    margin: 0 var(--spacing-md);
  }

  .app-header__actions {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    flex: 1;
    justify-content: flex-end;
    padding: 0 var(--spacing-xl);

    .header-action-item {
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }

  .user-dropdown {
    cursor: pointer;
    transition: var(--transition-base);

    &:hover {
      opacity: 0.8;
    }

    .user-info {
      @include flex-start;
      gap: var(--spacing-sm);
      padding: var(--spacing-sm) var(--spacing-md);
      border-radius: var(--radius-md);
      transition: var(--transition-base);

      &:hover {
        background: var(--bg-hover);
      }
    }

    .user-avatar {
      width: 32px;
      height: 32px;
      border-radius: var(--radius-full);
      border: 2px solid var(--border-light);
      transition: var(--transition-base);

      &:hover {
        border-color: var(--primary-color);
      }
    }

    .user-name {
      font-size: var(--font-size-sm);
      font-weight: var(--font-weight-medium);
      color: var(--text-primary);
      max-width: 120px;
      @include text-ellipsis;
    }

    .dropdown-icon {
      font-size: 16px;
      color: var(--text-tertiary);
      transition: var(--transition-base);
    }

    &:hover .dropdown-icon {
      color: var(--text-secondary);
      transform: rotate(180deg);
    }
  }

  .time-zone-description {
    margin: 0 0 var(--spacing-lg);
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
  }
}

// 下拉菜单样式
:deep(.user-dropdown-menu) {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: var(--spacing-xs);
  background: var(--bg-primary);

  .logout-item {
    @include flex-start;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-sm);
    transition: var(--transition-base);
    color: var(--text-secondary);

    &:hover {
      background: var(--danger-bg);
      color: var(--danger-color);
    }

    i {
      font-size: 16px;
    }
  }
}

// 响应式设计
@include mobile {
  .app-header {
    .app-header__content {
      padding: 0 var(--spacing-lg);
    }

    .brand-title {
      display: none;
    }

    .user-name {
      display: none;
    }
  }
}

@include tablet {
  .app-header {
    .app-header__content {
      padding: 0 var(--spacing-xl);
    }
  }
}
</style>
