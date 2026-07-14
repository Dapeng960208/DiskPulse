import { formatStorageTargetType, getStorageResourceNativeType } from '@/utils/storage-resource';

describe('storage resource presentation', () => {
  it('derives vendor-native resource types without changing API enums', () => {
    expect(getStorageResourceNativeType('aggregate', {
      storage_cluster: { storage_type: 'netapp' },
    })).toBe('NetApp Aggregate');
    expect(getStorageResourceNativeType('aggregate', {
      storage_cluster: { storage_type: 'isilon' },
    })).toBe('Isilon Storage Pool');
    expect(getStorageResourceNativeType('volume', {
      type: 'flexvol',
      storage_cluster: { storage_type: 'netapp' },
    })).toBe('NetApp Volume');
    expect(getStorageResourceNativeType('volume', {
      type: 'directory_quota',
      storage_cluster: { storage_type: 'isilon' },
    })).toBe('Isilon Directory Quota');
    expect(formatStorageTargetType('volume')).toBe('存储空间');
    expect(formatStorageTargetType('qtree')).toBe('Qtree（NetApp）');
  });
});
