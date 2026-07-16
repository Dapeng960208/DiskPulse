export function defaultStorageAlertRule() {
  return {
    quota_basis: 'hard',
    important: { threshold: 80, repeat_hours: 24 },
    serious: { threshold: 90, repeat_hours: 6 },
    emergency: { threshold: 95, repeat_hours: 1 },
  };
}
