import { useMediaQuery } from '@vueuse/core';

export function useResponsiveTableColumns() {
  return {
    showCapacityColumns: useMediaQuery('(min-width: 1024px)'),
    showSecondaryColumns: useMediaQuery('(min-width: 1440px)'),
  };
}
