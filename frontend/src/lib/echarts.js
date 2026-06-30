let echartsPromise;

export function loadEcharts() {
  if (!echartsPromise) {
    echartsPromise = import('echarts');
  }

  return echartsPromise;
}

export function getThemeVar(name, fallback = '') {
  if (typeof window === 'undefined') {
    return fallback;
  }

  return window.getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

export function getChartColors() {
  return [
    getThemeVar('--chart-color-primary', '#3B82F6'),
    getThemeVar('--chart-color-success', '#10B981'),
    getThemeVar('--chart-color-warning', '#F59E0B'),
    getThemeVar('--chart-color-danger', '#EF4444'),
    getThemeVar('--chart-color-info', '#06B6D4'),
    getThemeVar('--chart-color-muted', '#64748B'),
  ];
}

export function prefersReducedMotion() {
  return typeof window !== 'undefined'
    && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;
}
