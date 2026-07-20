export function formatCapacity(capacity, { emptyText = '-' } = {}) {
  if (!capacity || !Number.isFinite(Number(capacity.value)) || !capacity.unit) return emptyText;
  return `${capacity.value} ${capacity.unit}`;
}

export function formatCapacityFromGb(value, { emptyText = '-' } = {}) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return emptyText;
  const magnitude = Math.abs(numeric);
  const divisor = magnitude > 1024 * 1024 ? 1024 * 1024 : magnitude > 1024 ? 1024 : magnitude < 1 ? 1 / 1024 : 1;
  const unit = magnitude > 1024 * 1024 ? 'PB' : magnitude > 1024 ? 'TB' : magnitude < 1 ? 'MB' : 'GB';
  return `${Math.round((numeric / divisor) * 100) / 100} ${unit}`;
}
