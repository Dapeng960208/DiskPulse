import { formatCapacity, formatCapacityFromGb } from '@/utils/capacity';

export function formatQuotaLimit(value, { emptyText = '无硬限额' } = {}) {
  if (value === null || value === undefined) {
    return emptyText;
  }
  if (typeof value === 'object') return formatCapacity(value, { emptyText });
  if (Number(value) <= 0) return emptyText;
  return formatCapacityFromGb(value, { emptyText });
}

export function canRenderQuotaProgress({ used, total }) {
  return used !== null
    && used !== undefined
    && total !== null
    && total !== undefined
    && Number(used) >= 0
    && Number(total) > 0;
}
