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

export function getShortcuts() {
  return [
    { text: '8小时内', value: () => getDefaultTime(8) },
    { text: '1天内', value: () => getDefaultTime(24) },
    { text: '1周内', value: () => getDefaultTime(24 * 7) },
    { text: '1个月内', value: () => getDefaultTime(24 * 30) },
    { text: '3个月内', value: () => getDefaultTime(24 * 90) },
  ];
}
