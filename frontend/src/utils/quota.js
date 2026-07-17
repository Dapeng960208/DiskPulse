export function formatQuotaLimit(value, { emptyText = '无硬限额' } = {}) {
  if (value === null || value === undefined || Number(value) <= 0) {
    return emptyText;
  }

  const numericValue = Number(value);
  if (numericValue >= 1024) {
    return `${(numericValue / 1024).toFixed(1)} T`;
  }

  return `${numericValue} G`;
}

export function canRenderQuotaProgress({ used, total }) {
  return used !== null
    && used !== undefined
    && total !== null
    && total !== undefined
    && Number(used) >= 0
    && Number(total) > 0;
}
