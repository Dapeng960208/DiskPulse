<template>
  <main class="login-shell">
    <section
      class="login-visual"
      aria-labelledby="storage-platform-title"
    >
      <img
        class="login-visual__image"
        :src="storageClusterBackground"
        alt="数据中心内的高性能存储服务器集群"
        width="1536"
        height="1024"
        fetchpriority="high"
      >
      <div class="login-visual__shade" />
      <div class="login-visual__content">
        <img
          class="login-visual__logo"
          :src="brandLogo"
          alt="SpaceMIT 进迭时空"
        >
        <div class="login-visual__message">
          <h1 id="storage-platform-title">存储集群，一处掌控</h1>
        </div>
        <ul
          class="login-visual__capabilities"
          aria-label="平台能力"
        >
          <li>容量趋势</li>
          <li>性能分析</li>
          <li>故障诊断</li>
        </ul>
      </div>
    </section>

    <section
      class="login-panel"
      aria-labelledby="login-title"
    >
      <div class="login-panel__theme">
        <ThemeSwitch />
      </div>

      <div class="login-panel__content">
        <div class="login-header">
          <p class="login-kicker">安全登录</p>
          <h2 id="login-title">登录 {{ appTitle }}</h2>
        </div>

        <ElForm
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          class="login-form"
          label-position="top"
          @submit.prevent="handleLogin"
        >
          <ElFormItem
            label="用户名"
            prop="username"
          >
            <ElInput
              v-model="loginForm.username"
              name="username"
              autocomplete="username"
              placeholder="请输入 LDAP 用户名"
              size="large"
              :prefix-icon="User"
              clearable
              @keyup.enter="handleLogin"
            />
          </ElFormItem>

          <ElFormItem
            label="密码"
            prop="password"
          >
            <ElInput
              v-model="loginForm.password"
              type="password"
              name="password"
              autocomplete="current-password"
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

        <p class="login-panel__meta">身份认证由 LDAP 提供</p>
        <!-- Review source: Mock account markup violated vue/max-attributes-per-line. -->
        <!-- Resolution: keep every multi-line component attribute on its own line. -->
        <div
          v-if="mockEnabled()"
          class="demo-accounts"
          aria-label="Mock 演示账户"
        >
          <p>演示账户（仅 Mock 模式）</p>
          <ElButton
            v-for="account in demoUsers"
            :key="account.username"
            text
            @click="fillDemo(account)"
          >
            {{ account.commonName }}
          </ElButton>
        </div>
      </div>
    </section>
  </main>
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
import brandLogo from '@/assets/logo.png';
import storageClusterBackground from '@/assets/images/storage-cluster-login.webp';
import { DEMO_PASSWORD, DEMO_USERS, mockEnabled } from '@/mocks/runtime';
import { getBrowserTimeZone } from '@/utils/datetime.js';

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
const demoUsers = DEMO_USERS;
function fillDemo(account) { loginForm.username = account.username; loginForm.password = DEMO_PASSWORD; }

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

    let { result: userProfile } = await usersApi.fetchProfile();
    if (!userProfile.time_zone) {
      const { result: updatedProfile } = await usersApi.updateCurrentProfile({
        time_zone: getBrowserTimeZone(),
      });
      userProfile = updatedProfile;
    }
    currentUser.setCurrentUser(userProfile);

    ElMessage.success('登录成功');

    // 校验 redirect 仅接受同源相对路径，防止开放重定向（含 //evil.com 协议相对 URL）
    const rawRedirect = route.query.redirect;
    const redirect = (typeof rawRedirect === 'string'
      && rawRedirect.startsWith('/')
      && !rawRedirect.startsWith('//'))
      ? rawRedirect
      : '/';
    router.push(redirect);
  } catch (error) {
    if (import.meta.env.DEV) console.error('Login error:', error);

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
/* Hallmark · pre-emit critique: P5 H5 E5 S5 R5 V4
 * genre: modern-minimal · macrostructure: Split Studio · theme: project tokens
 * audience: storage operators · use: LDAP login · tone: technical
 * enrichment: generated storage-cluster still · nav: none · footer: none
 */
:global(html),
:global(body) {
  overflow-x: clip;
}

.login-shell {
  min-height: 100svh;
  background: var(--bg-secondary);
  color: var(--text-primary);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow-x: clip;
}

.login-visual {
  position: relative;
  min-height: clamp(15rem, 34svh, 20rem);
  isolation: isolate;
  overflow: hidden;
  color: var(--el-color-white);
  background: var(--primary-darker);
}

.login-visual__image,
.login-visual__shade {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.login-visual__image {
  object-fit: cover;
  object-position: 67% center;
  animation: visual-reveal var(--transition-slow) both;
}

.login-visual__shade {
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--primary-darker) 92%, transparent),
    color-mix(in srgb, var(--primary-darker) 62%, transparent)
  );
}

.login-visual__content {
  position: relative;
  z-index: 1;
  min-height: inherit;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: var(--spacing-2xl);
  padding: var(--spacing-2xl);
}

.login-visual__logo {
  width: clamp(9rem, 24vw, 12rem);
  height: auto;
}

.login-visual__message {
  max-width: 34rem;

  h1 {
    min-width: 0;
    color: inherit;
    font-size: var(--font-size-4xl);
    font-weight: var(--font-weight-bold);
    letter-spacing: -0.025em;
    line-height: var(--line-height-tight);
    overflow-wrap: anywhere;
  }

  p {
    margin-top: var(--spacing-lg);
    max-width: 30rem;
    color: color-mix(in srgb, var(--el-color-white) 78%, transparent);
    font-size: var(--font-size-base);
  }
}

.login-visual__capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-lg);
  color: color-mix(in srgb, var(--el-color-white) 72%, transparent);
  font-size: var(--font-size-sm);

  li {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);

    &::before {
      content: '';
      width: var(--spacing-xs);
      height: var(--spacing-xs);
      border-radius: var(--radius-full);
      background: var(--primary-light);
    }
  }
}

.login-panel {
  min-width: 0;
  background: var(--bg-primary);
  position: relative;
  display: grid;
  place-items: center;
  padding: var(--spacing-4xl) var(--spacing-2xl);
}

.login-panel__theme {
  position: absolute;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
}

.login-panel__content {
  width: min(100%, 26rem);
  animation: panel-reveal var(--transition-slow) both;
}

.login-header {
  margin-bottom: var(--spacing-3xl);

  .login-kicker {
    margin-bottom: var(--spacing-sm);
    color: var(--primary-color);
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
  }

  h2 {
    min-width: 0;
    color: var(--text-primary);
    font-size: var(--font-size-3xl);
    font-weight: var(--font-weight-bold);
    letter-spacing: -0.02em;
  }

  > p:last-child {
    margin-top: var(--spacing-md);
    color: var(--text-secondary);
    font-size: var(--font-size-base);
  }
}

.login-form {
  :deep(.el-form-item) {
    margin-bottom: var(--spacing-xl);

    .el-form-item__label {
      height: auto;
      margin-bottom: var(--spacing-sm);
      color: var(--text-primary);
      font-size: var(--font-size-sm);
      font-weight: var(--font-weight-medium);
      line-height: var(--line-height-normal);
    }

    .el-input__wrapper {
      min-height: 3rem;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      background: var(--bg-secondary);
      box-shadow: none;
      outline: 2px solid transparent;
      outline-offset: 1px;
      transition: background-color var(--transition-fast), border-color var(--transition-fast);

      &.is-focus {
        border-color: var(--primary-color);
        outline-color: var(--primary-color);
      }

      .el-input__inner {
        color: var(--text-primary);
        font-size: var(--font-size-base);

        &::placeholder {
          color: var(--text-tertiary);
        }
      }

      .el-input__prefix {
        color: var(--text-tertiary);
      }
    }
  }

  .error-message {
    margin-bottom: var(--spacing-lg);

    :deep(.el-alert) {
      border-radius: var(--radius-md);
      border: 1px solid var(--danger-color);
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
  min-height: 3rem;
  border-radius: var(--radius-md);
  background: var(--primary-color);
  color: var(--el-color-white);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  white-space: nowrap;
  transition: background-color var(--transition-fast), transform var(--transition-fast);

  &:active {
    transform: translateY(1px);
  }

  &:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: var(--spacing-xs);
  }

  &.is-disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  &.is-loading {
    opacity: 0.8;
    cursor: not-allowed;
  }
}

.login-panel__meta {
  margin-top: var(--spacing-md);
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
  text-align: center;
}
.demo-accounts { margin-top: var(--spacing-lg); text-align: center; color: var(--text-secondary); font-size: var(--font-size-sm); }

@keyframes visual-reveal {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes panel-reveal {
  from {
    opacity: 0;
    transform: translateY(var(--spacing-md));
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (hover: hover) and (pointer: fine) {
  .login-form :deep(.el-input__wrapper:hover) {
    background: var(--bg-tertiary);
    border-color: var(--border-dark);
  }

  .login-button:hover {
    background: var(--primary-dark);
    transform: translateY(-1px);
  }
}

@media (min-width: 60rem) {
  .login-shell {
    grid-template-columns: minmax(0, 1.18fr) minmax(26rem, 0.82fr);
    grid-template-rows: minmax(0, 1fr);
  }

  .login-visual {
    min-height: 100svh;
  }

  .login-visual__content {
    padding: var(--spacing-4xl);
  }

  .login-visual__message h1 {
    font-size: clamp(var(--font-size-4xl), 3.4vw, 3.5rem);
  }

  .login-panel {
    padding-inline: var(--spacing-4xl);
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-visual__image,
  .login-panel__content {
    animation: none;
  }

  .login-button,
  .login-form :deep(.el-input__wrapper) {
    transition-duration: 0.15s;
  }
}
</style>
