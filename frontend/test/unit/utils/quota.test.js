import { describe, expect, it } from 'vitest';
import { canRenderQuotaProgress, formatQuotaLimit } from '@/utils/quota';

describe('quota display helpers', () => {
  it('formats hard and soft quota values with explicit empty text', () => {
    expect(formatQuotaLimit(2048)).toBe('2 TB');
    expect(formatQuotaLimit(512)).toBe('512 GB');
    expect(formatQuotaLimit({ value: 1.5, unit: 'TB' })).toBe('1.5 TB');
    expect(formatQuotaLimit(null)).toBe('无硬限额');
    expect(formatQuotaLimit(0, { emptyText: '无软限额' })).toBe('无软限额');
  });

  it('only renders progress when both usage and quota are meaningful', () => {
    expect(canRenderQuotaProgress({ used: 20, total: 80 })).toBe(true);
    expect(canRenderQuotaProgress({ used: 20, total: null })).toBe(false);
    expect(canRenderQuotaProgress({ used: 20, total: 0 })).toBe(false);
  });
});
