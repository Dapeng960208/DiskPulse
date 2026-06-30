import { getDefaultTime, getShortcuts } from '@/utils/time-range';

describe('utils/time-range', () => {
  it('returns a start/end pair formatted as timestamps', () => {
    const [start, end] = getDefaultTime(8);

    expect(start).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
    expect(end).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
    expect(new Date(start).getTime()).toBeLessThanOrEqual(new Date(end).getTime());
  });

  it('exposes common quick ranges', () => {
    const shortcuts = getShortcuts();

    expect(shortcuts).toHaveLength(5);
    expect(shortcuts.map((item) => item.text)).toEqual([
      '8小时内',
      '1天内',
      '1周内',
      '1个月内',
      '3个月内',
    ]);
    expect(shortcuts[0].value()).toHaveLength(2);
  });
});
