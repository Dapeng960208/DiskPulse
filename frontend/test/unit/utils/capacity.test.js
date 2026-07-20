import { describe, expect, it } from 'vitest';
import { formatCapacity } from '@/utils/capacity';

describe('capacity display helper', () => {
  it('renders the unit and value supplied by the storage API', () => {
    expect(formatCapacity({ value: 512, unit: 'MB' })).toBe('512 MB');
    expect(formatCapacity({ value: 1.25, unit: 'TB' })).toBe('1.25 TB');
    expect(formatCapacity({ value: 1, unit: 'PB' })).toBe('1 PB');
  });

  it('uses the configured empty text when the API has no capacity value', () => {
    expect(formatCapacity(null, { emptyText: '无硬限额' })).toBe('无硬限额');
  });
});
