<script setup>
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { ElAside, ElBreadcrumb, ElBreadcrumbItem, ElContainer, ElMain, ElScrollbar, ElSpace } from 'element-plus';
import AppFooter from './components/AppFooter.vue';
import AppHeader from './components/AppHeader.vue';
import RouteMenu from './components/RouteMenu.vue';
import { useAppSettings } from '@/stores/app-settings';
import { buildBreadcrumbItems } from '@/utils/breadcrumbs';

defineProps({
  showAside: {
    type: Boolean,
    default: true,
  },
});

const appSettings = useAppSettings();
const route = useRoute();
const headerHeight = ref('60px');
const footerHeight = ref('40px');
const breadcrumbItems = computed(() => buildBreadcrumbItems(route.matched));
</script>

<template>
  <ElContainer
    class="app-layout"
    direction="vertical">
    <AppHeader :height="headerHeight" />
    <ElContainer class="app-layout__body">
      <ElAside
        v-if="showAside"
        id="app-aside"
        class="!w-auto border-r border-[var(--el-border-color)]">
        <ElScrollbar class="h-full">
          <RouterView
            v-slot="{ Component }"
            name="aside">
            <template v-if="Component">
              <component :is="Component" />
            </template>
            <RouteMenu
              v-else
              width="240px" />
          </RouterView>
        </ElScrollbar>
      </ElAside>
      <ElContainer
        class="app-layout__workspace"
        direction="vertical">
        <ElMain class="app-main">
          <div class="py-4">
            <ElSpace align="center">
              <button
                v-if="showAside"
                data-testid="aside-collapse-toggle"
                class="aside-collapse-toggle"
                type="button"
                :aria-controls="'app-aside'"
                :aria-expanded="String(!appSettings.asideCollapsed)"
                :aria-label="appSettings.asideCollapsed ? '展开侧边导航' : '收起侧边导航'"
                @click="appSettings.toggleAsideCollapsed()">
                <i
                  v-if="appSettings.asideCollapsed"
                  class="i-ri-menu-unfold-fill"></i>
                <i
                  v-else
                  class="i-ri-menu-fold-fill"></i>
              </button>
              <ElBreadcrumb>
                <ElBreadcrumbItem
                  v-for="breadcrumbItem of breadcrumbItems"
                  :key="breadcrumbItem"
                >
                  {{ breadcrumbItem }}
                </ElBreadcrumbItem>
              </ElBreadcrumb>
            </ElSpace>
          </div>
          <ElScrollbar
            class="app-main__scrollbar"
            wrap-class="app-main__content-wrap"
            view-class="h-full flex flex-col">
            <div class="flex-1 min-h-0 flex flex-col">
              <RouterView v-slot="{ Component, route }">
                <template v-if="Component">
                  <KeepAlive>
                    <component
                      :is="Component"
                      v-if="route.meta.keepAlive"
                      :key="route.name" />
                  </KeepAlive>
                  <component
                    :is="Component"
                    v-if="!route.meta.keepAlive" />
                </template>
                <div
                  v-else
                  class="flex justify-center">
                  页面正在建设中...
                </div>
              </RouterView>
            </div>
          </ElScrollbar>
        </ElMain>
        <AppFooter
          class="flex-shrink-0"
          :height="footerHeight" />
      </ElContainer>
    </ElContainer>
  </ElContainer>
</template>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';

.app-layout {
  height: 100vh;
  background: var(--bg-secondary);
}

.app-layout__body,
.app-layout__workspace {
  min-width: 0;
  min-height: 0;
}

.app-main {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  padding: 0;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--bg-secondary);

  .app-main__scrollbar {
    flex: 1 1 auto;
    min-height: 0;
  }

  :deep(.app-main__content-wrap) {
    padding: var(--spacing-lg);
  }

  // 面包屑区域
  .py-4 {
    padding: var(--spacing-lg) 0;
    border-bottom: 1px solid var(--border-light);
    background: var(--bg-primary);
    padding-left: var(--spacing-lg);
    padding-right: var(--spacing-lg);

    :deep(.el-breadcrumb) {
      .el-breadcrumb__item {
        .el-breadcrumb__inner {
          color: var(--text-secondary);
          font-size: var(--font-size-sm);
          font-weight: var(--font-weight-medium);
        }

        &:last-child .el-breadcrumb__inner {
          color: var(--primary-color);
        }
      }

      .el-breadcrumb__separator {
        color: var(--text-tertiary);
      }
    }

    // 菜单折叠按钮
    .aside-collapse-toggle {
      appearance: none;
      border: 0;
      background: transparent;
      cursor: pointer;
      padding: var(--spacing-sm);
      border-radius: var(--radius-sm);
      color: var(--text-secondary);
      transition: var(--transition-base);
      display: inline-flex;
      align-items: center;
      justify-content: center;

      &:hover {
        background: var(--bg-hover);
        color: var(--primary-color);
      }

      &:focus-visible {
        outline: 2px solid var(--primary-color);
        outline-offset: 2px;
      }

      i {
        font-size: 18px;
      }
    }
  }

  .app-main__content-container {
    min-width: 0;

    .app-main__content {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
  }
}

// 侧边栏样式
:deep(.el-aside) {
  background: var(--bg-primary);
  border-right: 1px solid var(--border-color);
  transition: var(--transition-base);

  .el-scrollbar {
    .el-scrollbar__wrap {
      @include custom-scrollbar;
    }
  }
}

// 主内容区滚动条
:deep(.el-scrollbar) {
  .el-scrollbar__wrap {
    @include custom-scrollbar;
  }
}

// 响应式设计
@include mobile {
  .app-main {
    :deep(.app-main__content-wrap) {
      padding: var(--spacing-md);
    }

    .py-4 {
      padding-left: var(--spacing-md);
      padding-right: var(--spacing-md);
    }
  }
}
</style>
