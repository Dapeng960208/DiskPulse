<script setup>
import { nextTick } from 'vue';
import { useAppSettings } from '@/stores/app-settings';

const props = defineProps({
  animated: {
    type: Boolean,
    default: true,
  },
});

const appSettings = useAppSettings();

async function toggle({ clientX: x, clientY: y }) {
  if (props.animated) {
    const canAnimate = 'startViewTransition' in document
      && window.matchMedia('(prefers-reduced-motion: no-preference)').matches;

    if (canAnimate) {
      const clipPath = [
        `circle(0px at ${x}px ${y}px)`,
        `circle(${Math.hypot(
          Math.max(x, innerWidth - x),
          Math.max(y, innerHeight - y),
        )}px at ${x}px ${y}px)`,
      ];
      let isDark;

      await document.startViewTransition(async () => {
        isDark = appSettings.toggleTheme();
        await nextTick();
      }).ready;

      document.documentElement.animate(
        { clipPath: isDark ? clipPath.reverse() : clipPath },
        {
          duration: 500,
          easing: 'ease-in-out',
          pseudoElement: `::view-transition-${isDark ? 'old' : 'new'}(root)`,
        },
      );
    } else {
      appSettings.toggleTheme();
    }
  } else {
    appSettings.toggleTheme();
  }
}
</script>

<template>
  <button
    class="theme-switch"
    type="button"
    :aria-label="appSettings.theme === 'dark' ? '切换到亮色模式' : '切换到暗色模式'"
    :aria-pressed="String(appSettings.theme === 'dark')"
    :title="appSettings.theme === 'dark' ? '切换到亮色模式' : '切换到暗色模式'"
    @click="toggle">
    <i
      v-if="appSettings.theme === 'dark'"
      class="i-ri-moon-line theme-icon"></i>
    <i
      v-else
      class="i-ri-sun-line theme-icon"></i>
  </button>
</template>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.theme-switch {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  cursor: pointer;
  transition: var(--transition-all);
  color: var(--text-secondary);
  padding: 0;

  &:hover {
    background: var(--bg-hover);
    border-color: var(--primary-color);
    color: var(--primary-color);
    transform: scale(1.05);
  }

  &:active {
    transform: scale(0.95);
  }

  &:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }

  .theme-icon {
    display: inline-flex;
    width: 18px;
    height: 18px;
    font-size: 18px;
    line-height: 1;
    flex-shrink: 0;
    transition: var(--transition-base);
  }
}
</style>

<style>
::view-transition-old(root),
::view-transition-new(root) {
  animation: none;
  mix-blend-mode: normal;
}

::view-transition-old(root),
.dark::view-transition-new(root) {
  z-index: 1;
}

::view-transition-new(root),
.dark::view-transition-old(root) {
  z-index: 9999;
}
</style>
