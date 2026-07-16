export function defaultStorageAlertRule() {
  return {
    quota_basis: 'hard',
    important: { threshold: 80, repeat_hours: 24 },
    serious: { threshold: 90, repeat_hours: 6 },
    emergency: { threshold: 95, repeat_hours: 1 },
  };
}

export function defaultStorageAlertThresholds() {
  return { important: 80, serious: 90, emergency: 95 };
}

export function getQuotaProgressColor(percentage, thresholds = defaultStorageAlertThresholds()) {
  if (percentage < thresholds.important) return '#34D399';
  if (percentage < thresholds.serious) return '#F59E0B';
  if (percentage <= thresholds.emergency) return '#EF4444';
  return '#B91C1C';
}
