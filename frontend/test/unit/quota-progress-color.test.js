import { getQuotaProgressColor } from '@/utils/storage-alert-rule';

describe('quota progress colors', () => {
  const thresholds = { important: 80, serious: 90, emergency: 95 };

  it.each([
    [79.99, '#34D399'],
    [80, '#F59E0B'],
    [89.99, '#F59E0B'],
    [90, '#EF4444'],
    [95, '#EF4444'],
    [95.01, '#B91C1C'],
  ])('maps %s percent to %s', (percentage, color) => {
    expect(getQuotaProgressColor(percentage, thresholds)).toBe(color);
  });

  it('uses non-default global thresholds', () => {
    const custom = { important: 70, serious: 85, emergency: 93 };

    expect(getQuotaProgressColor(70, custom)).toBe('#F59E0B');
    expect(getQuotaProgressColor(85, custom)).toBe('#EF4444');
    expect(getQuotaProgressColor(93.01, custom)).toBe('#B91C1C');
  });
});
