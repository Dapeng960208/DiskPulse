export function getStorageResourceNativeType(resourceType, resource) {
  const storageType = resource?.storage_cluster?.storage_type;
  if (resourceType === 'aggregate') {
    if (storageType === 'isilon') return 'Isilon Storage Pool';
    if (storageType === 'netapp') return 'NetApp Aggregate';
  }
  if (resourceType === 'volume') {
    if (storageType === 'isilon' || resource?.type === 'directory_quota') {
      return 'Isilon Directory Quota';
    }
    if (storageType === 'netapp') return 'NetApp Volume';
  }
  return resource?.type || '-';
}

export function formatStorageTargetType(type) {
  return { volume: '存储空间', qtree: 'Qtree（NetApp）' }[type?.toLowerCase()] || type || '-';
}
