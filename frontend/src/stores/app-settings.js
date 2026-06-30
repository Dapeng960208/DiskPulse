import { useDark, useToggle } from '@vueuse/core';
import { defineStore } from 'pinia';
import { computed } from 'vue';

export const useAppSettings = defineStore('app', () => {
  const [asideCollapsed, toggleAsideCollapsed] = useToggle();
  const isDark = useDark({
    storageKey: `${import.meta.env.VITE_APP_ID}:theme`,
  });
  const theme = computed(() => isDark.value ? 'dark' : 'light');
  const toggleTheme = useToggle(isDark);

  return {
    asideCollapsed,
    theme,
    toggleAsideCollapsed,
    toggleTheme,
  };
});
