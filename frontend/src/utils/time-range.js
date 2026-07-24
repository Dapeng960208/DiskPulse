function formatDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

export function getDefaultTime(hour) {
  const end = new Date();
  const start = new Date();

  start.setTime(start.getTime() - 3600 * 1000 * hour);

  return [formatDate(start), formatDate(end)];
}

const SHORTCUT_DEFINITIONS = [
  { text: '1天内', hours: 24 },
  { text: '3天内', hours: 24 * 3 },
  { text: '1周内', hours: 24 * 7 },
  { text: '1个月内', hours: 24 * 30 },
  { text: '3个月内', hours: 24 * 90 },
  { text: '6个月内', hours: 24 * 180 },
  { text: '1年内', hours: 24 * 365 },
];

export function getShortcuts(maxDays) {
  const maxHours = Number.isFinite(maxDays) ? maxDays * 24 : Number.POSITIVE_INFINITY;

  // Consumers with stricter backend query limits must not expose shortcuts
  // that can only produce a rejected request.
  return SHORTCUT_DEFINITIONS
    .filter(({ hours }) => hours <= maxHours)
    .map(({ text, hours }) => ({
      text,
      value: () => getDefaultTime(hours),
    }));
}
