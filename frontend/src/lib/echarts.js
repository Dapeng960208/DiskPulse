let echartsPromise;

export function loadECharts() {
  echartsPromise ||= import('echarts');
  return echartsPromise;
}

export function loadEcharts() {
  return loadECharts();
}

export function getCssColor(variable, fallback) {
  if (typeof document === 'undefined') return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(variable).trim() || fallback;
}

export function getThemeVar(name, fallback = '') {
  return getCssColor(name, fallback);
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
