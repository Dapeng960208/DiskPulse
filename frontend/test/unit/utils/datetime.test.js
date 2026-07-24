import { formatDateTime, getBrowserTimeZone, toUtcRange } from '@/utils/datetime.js';

describe('datetime presentation contract', () => {
  it('formats the same UTC instant in the saved user timezone', () => {
    const instant = '2026-07-23T02:30:00Z';

    expect(formatDateTime(instant, 'Asia/Shanghai')).toContain('2026/07/23 10:30:00');
    expect(formatDateTime(instant, 'America/New_York')).toContain('2026/07/22 22:30:00');
  });

  it('turns a local range in the selected user timezone into RFC 3339 UTC bounds', () => {
    expect(toUtcRange(['2026-07-23 10:30:00', '2026-07-23 11:30:00'], 'Asia/Shanghai')).toEqual([
      '2026-07-23T02:30:00Z',
      '2026-07-23T03:30:00Z',
    ]);
  });

  it('uses Asia/Shanghai only when the browser does not expose a valid IANA timezone', () => {
    expect(getBrowserTimeZone(() => 'America/New_York')).toBe('America/New_York');
    expect(getBrowserTimeZone(() => '')).toBe('Asia/Shanghai');
  });
});
