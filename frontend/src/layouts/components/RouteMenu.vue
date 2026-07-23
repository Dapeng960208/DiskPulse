<script setup>
import { useRoute, useRouter } from 'vue-router';
import { ref, watch } from 'vue';
import { ElMenu } from 'element-plus';
import RouteMenuItem from './RouteMenuItem.vue';
import { useAppSettings } from '@/stores/app-settings';

defineProps({
  width: {
    type: String,
  },
});
const route = useRoute();
const router = useRouter();
const menuOptions = router
  .getRoutes()
  .filter((route) => route.meta.isRoot)
  .sort((left, right) => left.meta.menuOrder - right.meta.menuOrder)
  .map((route) => mapRouteToMenuOption(route))
  .filter((option) => option.isVisible());
const appSettings = useAppSettings();
const currentPath = ref(route.path);
const expanded = ref([route.path.slice(0, route.path.lastIndexOf('/'))]);

watch(() => route.path, (value) => {
  currentPath.value = value;
  expanded.value = [...expanded.value, route.path.slice(0, route.path.lastIndexOf('/'))];
});

function mapRouteToMenuOption(route, parentPath) {
  const path = parentPath
    ? [parentPath, route.path].filter(Boolean).join('/').replace(/\/{2,}/g, '/')
    : route.path;
  const key = route.name || route.meta.menuKey || `${parentPath || 'root'}:${route.meta.title}`;
  const index = route.path || !parentPath
    ? path
    : `${parentPath}#${route.meta.menuKey || route.meta.title}`;

  return {
    key,
    index,
    label: route.meta.title,
    icon: route.meta.icon,
    section: route.meta.menuSection,
    path,
    children:
      route.children && route.children.length > 0
        ? route.children.map((childRoute) =>
          mapRouteToMenuOption(childRoute, path),
        )
        : undefined,
    hideOnSingleChild: route.meta.hideOnSingleChild,
    isVisible() {
      return route.meta.isHidden !== true && (route.meta.isAccessible ? route.meta.isAccessible() === 200 : true);
    },
  };
}
</script>

<template>
  <ElMenu
    class="route-menu !border-none"
    :default-active="$route.path"
    :collapse="appSettings.asideCollapsed"
    router
  >
    <RouteMenuItem
      v-for="menuOption of menuOptions"
      :key="menuOption.key"
      :option="menuOption" />
  </ElMenu>
</template>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.route-menu:not(.el-menu--collapse) {
  width: v-bind(width);
}

.route-menu {
  background: var(--bg-primary);
  border-right: none !important;
  padding: var(--spacing-sm) var(--spacing-xs);

  :deep(.el-menu-item) {
    height: 44px;
    line-height: 44px;
    border-radius: var(--radius-md);
    margin: 2px 0;
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    transition: var(--transition-all);

    &:hover {
      background: var(--bg-hover);
      color: var(--primary-color);
    }

    &.is-active {
      background: var(--bg-hover);
      color: var(--primary-color);
      font-weight: var(--font-weight-medium);
      position: relative;

      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 3px;
        height: 20px;
        background: var(--primary-gradient);
        border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
      }
    }
  }

  :deep(.el-sub-menu) {
    .el-sub-menu__title {
      height: 44px;
      line-height: 44px;
      border-radius: var(--radius-md);
      margin: 2px 0;
      font-size: var(--font-size-sm);
      color: var(--text-secondary);
      transition: var(--transition-all);

      &:hover {
        background: var(--bg-hover);
        color: var(--primary-color);
      }
    }

    &.is-opened > .el-sub-menu__title {
      color: var(--primary-color);
    }

    .el-menu {
      background: transparent;
      padding-left: var(--spacing-sm);

      .el-menu-item {
        height: 40px;
        line-height: 40px;
        font-size: var(--font-size-sm);
        padding-left: 40px !important;
      }
    }
  }

  // 折叠状态
  &.el-menu--collapse {
    padding: var(--spacing-sm) var(--spacing-xs);

    :deep(.el-menu-item),
    :deep(.el-sub-menu__title) {
      border-radius: var(--radius-md);
      margin: 2px 0;
    }
  }
}
</style>
