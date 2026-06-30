<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1 class="login-title">{{ appTitle }}</h1>
        <p class="login-subtitle">欢迎登录</p>
      </div>

      <ElForm
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <ElFormItem prop="username">
          <ElInput
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
            clearable
            @keyup.enter="handleLogin"
          />
        </ElFormItem>

        <ElFormItem prop="password">
          <ElInput
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            clearable
            @keyup.enter="handleLogin"
          />
        </ElFormItem>

        <ElFormItem
          v-if="errorMessage"
          class="error-message">
          <ElAlert
            :title="errorMessage"
            type="error"
            :closable="false"
            show-icon
          />
        </ElFormItem>

        <ElFormItem>
          <ElButton
            type="primary"
            size="large"
            :loading="loading"
            class="login-button"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登录' }}
          </ElButton>
        </ElFormItem>
      </ElForm>

      <div class="login-footer">
        <ThemeSwitch />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { User, Lock } from '@element-plus/icons-vue';
import { ElMessage,ElForm,ElFormItem,ElInput,ElAlert,ElButton } from 'element-plus';
import usersApi from '@/api/users-api';
import { setToken } from '@/utils/authorization';
import { useCurrentUser } from '@/stores/current-user';
import ThemeSwitch from '@/components/basic/ThemeSwitch.vue';

const appTitle = import.meta.env.VITE_APP_TITLE || 'DiskPulse 管理后台';

const router = useRouter();
const route = useRoute();
const currentUser = useCurrentUser();

const loginFormRef = ref(null);
const loading = ref(false);
const errorMessage = ref('');

const loginForm = reactive({
  username: '',
  password: '',
});

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, message: '用户名长度至少为2个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少为6个字符', trigger: 'blur' },
  ],
};

const handleLogin = async () => {
  if (!loginFormRef.value) return;

  try {
    const valid = await loginFormRef.value.validate();
    if (!valid) return;

    loading.value = true;
    errorMessage.value = '';

    const { result } = await usersApi.login(loginForm.username, loginForm.password);

    if (result.token) {
      setToken(result.token);
    }

    const { result: userProfile } = await usersApi.fetchProfile();
    currentUser.setCurrentUser(userProfile);

    ElMessage.success('登录成功');

    const redirect = route.query.redirect || '/';
    router.push(redirect);
  } catch (error) {
    console.error('Login error:', error);

    if (error.response) {
      const status = error.response.status;
      if (status === 401) {
        errorMessage.value = '用户名或密码错误';
      } else if (status === 403) {
        errorMessage.value = '账号已被禁用';
      } else if (status === 429) {
        errorMessage.value = '登录尝试次数过多，请稍后再试';
      } else {
        errorMessage.value = '登录失败，请稍后重试';
      }
    } else {
      errorMessage.value = '网络错误，请检查网络连接';
    }
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  // 自动聚焦到用户名输入框
  const usernameInput = document.querySelector('input[type="text"]');
  if (usernameInput) {
    usernameInput.focus();
  }
});
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';

.login-container {
  @include flex-center;
  min-height: 100vh;
  background: var(--primary-gradient);
  padding: var(--spacing-xl);
  position: relative;
  overflow: hidden;

  // 背景装饰
  &::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
    background-size: 50px 50px;
    animation: float 20s ease-in-out infinite;
  }

  &::after {
    content: '';
    position: absolute;
    top: 20%;
    right: 10%;
    width: 300px;
    height: 300px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 50%;
    animation: pulse 4s ease-in-out infinite;
  }
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-2xl);
  padding: var(--spacing-4xl);
  position: relative;
  z-index: 1;
  animation: slideUp 0.6s ease-out;
  border: 1px solid var(--border-light);

  @include backdrop-blur;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(40px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(180deg); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.05; }
  50% { transform: scale(1.1); opacity: 0.1; }
}

.login-header {
  text-align: center;
  margin-bottom: var(--spacing-3xl);

  .login-title {
    font-size: var(--font-size-4xl);
    font-weight: var(--font-weight-bold);
    color: var(--text-primary);
    margin: 0 0 var(--spacing-md) 0;
    background: var(--primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .login-subtitle {
    font-size: var(--font-size-lg);
    color: var(--text-secondary);
    margin: 0;
    font-weight: var(--font-weight-medium);
  }
}

.login-form {
  :deep(.el-form-item) {
    margin-bottom: var(--spacing-xl);

    .el-input {
      .el-input__wrapper {
        height: 48px;
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border-color);
        transition: var(--transition-all);

        @include input-focus;

        &:hover {
          border-color: var(--border-dark);
          box-shadow: var(--shadow-md);
        }

        .el-input__inner {
          font-size: var(--font-size-base);
          color: var(--text-primary);
          padding-left: var(--spacing-lg);

          &::placeholder {
            color: var(--text-disabled);
          }
        }

        .el-input__prefix {
          color: var(--text-tertiary);
        }
      }
    }
  }

  .error-message {
    margin-bottom: var(--spacing-lg);

    :deep(.el-alert) {
      border-radius: var(--radius-md);
      border: none;
      background: var(--danger-bg);

      .el-alert__content {
        .el-alert__title {
          color: var(--danger-color);
          font-size: var(--font-size-sm);
        }
      }
    }
  }
}

.login-button {
  width: 100%;
  height: 48px;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  border-radius: var(--radius-lg);
  @include button-primary;

  @include flex-center;

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
  }

  &:active {
    transform: translateY(0);
  }

  &.is-loading {
    opacity: 0.8;
    cursor: not-allowed;
  }
}

.login-footer {
  margin-top: var(--spacing-3xl);
  display: flex;
  justify-content: center;
  align-items: center;
  padding-top: var(--spacing-xl);
  border-top: 1px solid var(--border-light);
}

// 响应式设计
@include mobile {
  .login-container {
    padding: var(--spacing-lg);
  }

  .login-card {
    padding: var(--spacing-3xl) var(--spacing-xl);
  }

  .login-header {
    .login-title {
      font-size: var(--font-size-3xl);
    }
  }
}

@include tablet {
  .login-card {
    max-width: 380px;
  }
}

// 暗色主题适配
html.dark {
  .login-container {
    &::before {
      background: radial-gradient(circle, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
    }

    &::after {
      background: rgba(255, 255, 255, 0.02);
    }
  }
}
</style>
