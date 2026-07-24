import { vi } from 'vitest';
import { getDefaultTime, getShortcuts } from '@/utils/time-range';

describe('utils/time-range', () => {
  it('returns a start/end pair formatted as timestamps', () => {
    const [start, end] = getDefaultTime(8);

    expect(start).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
    expect(end).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
    expect(new Date(start).getTime()).toBeLessThanOrEqual(new Date(end).getTime());
  });

  it('exposes the seven required quick ranges in a consistent order', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-07-24T08:00:00'));
    const shortcuts = getShortcuts();

    expect(shortcuts).toHaveLength(7);
    expect(shortcuts.map((item) => item.text)).toEqual([
      '1天内',
      '3天内',
      '1周内',
      '1个月内',
      '3个月内',
      '6个月内',
      '1年内',
    ]);
    const expectedHours = [24, 24 * 3, 24 * 7, 24 * 30, 24 * 90, 24 * 180, 24 * 365];
    shortcuts.forEach((shortcut, index) => {
      const range = shortcut.value();

      expect(range).toHaveLength(2);
      expect(range[0]).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
      expect(range[1]).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
      expect(new Date(range[1]).getTime() - new Date(range[0]).getTime())
        .toBe(expectedHours[index] * 60 * 60 * 1000);
    });
    vi.useRealTimers();
  });
});
