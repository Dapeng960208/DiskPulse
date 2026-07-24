import { ref } from 'vue';

const FALLBACK_TIME_ZONE = 'Asia/Shanghai';
const presentationTimeZone = ref(FALLBACK_TIME_ZONE);

function validTimeZone(value) {
  if (!value || typeof value !== 'string') return false;
  try {
    Intl.DateTimeFormat('en-US', { timeZone: value });
    return true;
  } catch {
    return false;
  }
}

function partsFor(value, timeZone) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(value)).reduce((parts, part) => ({ ...parts, [part.type]: part.value }), {});
}

function offsetMilliseconds(instant, timeZone) {
  const value = new Intl.DateTimeFormat('en-US', {
    timeZone,
    timeZoneName: 'longOffset',
  }).formatToParts(new Date(instant)).find((part) => part.type === 'timeZoneName')?.value;
  const match = /^GMT(?:(?<sign>[+-])(?<hours>\d{1,2})(?::(?<minutes>\d{2}))?)?$/.exec(value || '');
  if (!match) return 0;
  const total = (Number(match.groups.hours || 0) * 60 + Number(match.groups.minutes || 0)) * 60 * 1000;
  return match.groups.sign === '-' ? -total : total;
}

function parseLocalDateTime(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/.exec(value || '');
  if (!match) throw new TypeError('time range values must use YYYY-MM-DD HH:mm:ss');
  return match.slice(1).map(Number);
}

export function getBrowserTimeZone(read = () => Intl.DateTimeFormat().resolvedOptions().timeZone) {
  const candidate = read();
  return validTimeZone(candidate) ? candidate : FALLBACK_TIME_ZONE;
}

export function setPresentationTimeZone(value) {
  presentationTimeZone.value = validTimeZone(value) ? value : FALLBACK_TIME_ZONE;
}

export function getPresentationTimeZone() {
  return presentationTimeZone.value;
}

export function formatDateTime(value, timeZone = presentationTimeZone.value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  const parts = partsFor(date, validTimeZone(timeZone) ? timeZone : FALLBACK_TIME_ZONE);
  return `${parts.year}/${parts.month}/${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`;
}

export function formatDate(value, timeZone = presentationTimeZone.value) {
  return formatDateTime(value, timeZone).split(' ')[0];
}

export function localDateTimeToUtc(value, timeZone = presentationTimeZone.value) {
  const [year, month, day, hour, minute, second] = parseLocalDateTime(value);
  const resolvedTimeZone = validTimeZone(timeZone) ? timeZone : FALLBACK_TIME_ZONE;
  let instant = Date.UTC(year, month - 1, day, hour, minute, second);
  instant -= offsetMilliseconds(instant, resolvedTimeZone);
  instant -= offsetMilliseconds(instant, resolvedTimeZone) - offsetMilliseconds(
    Date.UTC(year, month - 1, day, hour, minute, second),
    resolvedTimeZone,
  );
  return new Date(instant).toISOString().replace('.000Z', 'Z');
}

export function toUtcRange(range, timeZone = presentationTimeZone.value) {
  if (!Array.isArray(range) || range.length !== 2) return [];
  return range.map((value) => localDateTimeToUtc(value, timeZone));
}
