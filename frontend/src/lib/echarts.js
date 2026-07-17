let echartsPromise;

export function loadECharts() {
  echartsPromise ||= import('echarts');
  return echartsPromise;
}

export function getCssColor(variable, fallback) {
  if (typeof document === 'undefined') return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(variable).trim() || fallback;
}
