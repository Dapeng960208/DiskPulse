const LEVELS = ['important', 'serious', 'emergency'];
const LEVEL_LABELS = { important: '重要', serious: '严重', emergency: '紧急' };
const RULE_SOURCE_LABELS = { system: '系统规则', project: '项目规则', group: '项目组规则' };

const pointValue = (point) => (Array.isArray(point) ? point : point?.value);

function finiteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function interpolatedTime(start, end, ratio) {
  const startTime = new Date(start).getTime();
  const endTime = new Date(end).getTime();
  if (Number.isFinite(startTime) && Number.isFinite(endTime)) {
    return startTime + (endTime - startTime) * ratio;
  }
  const startNumber = finiteNumber(start);
  const endNumber = finiteNumber(end);
  return startNumber !== null && endNumber !== null
    ? startNumber + (endNumber - startNumber) * ratio
    : start;
}

export function insertThresholdCrossings(data = [], thresholds = []) {
  if (data.length < 2 || !thresholds.length) {
    return data.map((point) => ({ value: pointValue(point), synthetic: false }));
  }

  const output = [];
  data.forEach((point, index) => {
    const value = pointValue(point);
    output.push({ value, synthetic: false });
    if (index === data.length - 1) return;

    const next = pointValue(data[index + 1]);
    const startValue = finiteNumber(value?.[1]);
    const endValue = finiteNumber(next?.[1]);
    if (startValue === null || endValue === null || startValue === endValue) return;

    const crossed = thresholds
      .filter((threshold) => threshold > Math.min(startValue, endValue)
        && threshold < Math.max(startValue, endValue))
      .sort((left, right) => (endValue > startValue ? left - right : right - left));
    crossed.forEach((threshold) => {
      const ratio = (threshold - startValue) / (endValue - startValue);
      output.push({
        value: [interpolatedTime(value[0], next[0], ratio), threshold],
        synthetic: true,
      });
    });
  });
  return output;
}

function thresholdPercentages(meta, systemThresholds, multiple, percentage) {
  const source = multiple && percentage && systemThresholds
    ? systemThresholds
    : meta?.thresholds;
  if (!source) return [];
  return LEVELS
    .map((level) => ({ level, percentage: finiteNumber(source[level]) }))
    .filter(({ percentage: value }) => value !== null);
}

function thresholdValues({ indicator, trendMeta, systemThresholds, multiple }) {
  const percentage = indicator === 'use_ratio' || indicator === 'alert_ratio';
  const definitions = thresholdPercentages(trendMeta, systemThresholds, multiple, percentage);
  if (percentage) return definitions.map((item) => ({ ...item, value: item.percentage }));
  if (indicator !== 'used' || multiple) return [];
  const limit = finiteNumber(trendMeta?.quota_limit_gb);
  if (limit === null || limit <= 0) return [];
  return definitions.map((item) => ({ ...item, value: limit * item.percentage / 100 }));
}

function formatValue(value, unit) {
  const number = finiteNumber(value);
  if (number === null) return '-';
  if (unit === 'G' && Math.abs(number) >= 1024) return `${(number / 1024).toFixed(2)} T`;
  return `${number.toFixed(2)} ${unit}`.trim();
}

function formatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('zh-CN', { hour12: false });
}

function visualPieces(values, palette) {
  if (values.length !== 3) return [];
  return [
    { lt: values[0].value, color: palette.normal },
    { gte: values[0].value, lt: values[1].value, color: palette.important },
    { gte: values[1].value, lt: values[2].value, color: palette.serious },
    { gte: values[2].value, color: palette.emergency },
  ];
}

function markLine(values, palette) {
  if (!values.length) return undefined;
  const colors = {
    important: palette.important,
    serious: palette.serious,
    emergency: palette.emergency,
  };
  return {
    silent: true,
    symbol: 'none',
    data: values.map(({ level, percentage: threshold, value }) => ({
      yAxis: value,
      label: {
        show: true,
        position: 'end',
        align: 'left',
        verticalAlign: 'bottom',
        offset: [8, -6],
        color: colors[level],
        formatter: `${LEVEL_LABELS[level]} ${threshold}%`,
      },
      lineStyle: {
        color: colors[level],
        type: 'dashed',
        width: 1,
        opacity: 0.52,
      },
    })),
  };
}

function currentLevelLabel(value, thresholds) {
  const number = finiteNumber(value);
  if (number === null) return '未知';
  const matched = [...thresholds].reverse().find((threshold) => number >= threshold.value);
  return matched ? LEVEL_LABELS[matched.level] : '正常';
}

export function buildStorageTrendOption({
  series = [],
  indicator = 'used',
  trendMeta = null,
  systemThresholds = null,
  unit = indicator === 'use_ratio' || indicator === 'alert_ratio' ? '%' : 'G',
  palette,
}) {
  const multiple = series.length > 1;
  const percentage = indicator === 'use_ratio' || indicator === 'alert_ratio';
  const values = thresholdValues({ indicator, trendMeta, systemThresholds, multiple });
  const pieces = !multiple ? visualPieces(values, palette) : [];
  const basisLabel = trendMeta?.quota_basis === 'soft' ? '软限额' : '硬限额';
  const ruleSourceLabel = RULE_SOURCE_LABELS[trendMeta?.rule_source] || '系统规则';

  const chartSeries = series.map((item, index) => ({
    name: item.name,
    type: 'line',
    smooth: 0.25,
    smoothMonotone: 'x',
    showSymbol: false,
    connectNulls: false,
    emphasis: { focus: 'series' },
    lineStyle: {
      width: 2.5,
      color: multiple ? palette.series[index % palette.series.length] : palette.normal,
    },
    data: !multiple && pieces.length
      ? insertThresholdCrossings(item.data, values.map(({ value }) => value))
      : item.data,
    markLine: index === 0 ? markLine(values, palette) : undefined,
  }));

  const option = {
    animationDuration: 300,
    color: palette.series,
    grid: { left: 12, right: 92, top: 24, bottom: 20, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { type: 'dashed', color: palette.axis } },
      formatter: (params = []) => {
        const items = Array.isArray(params) ? params : [params];
        if (!items.length) return '';
        const lines = [formatTime(items[0].axisValue)];
        items.forEach((item) => {
          const raw = pointValue(item.data);
          lines.push(`${item.marker || ''}${item.seriesName}: ${formatValue(raw?.[1] ?? item.value?.[1], unit)}`);
        });
        if (multiple) {
          lines.push('对比口径：系统阈值');
        } else {
          const raw = pointValue(items[0].data);
          lines.push(`当前等级：${currentLevelLabel(raw?.[1] ?? items[0].value?.[1], values)} · ${basisLabel} · ${ruleSourceLabel}`);
        }
        return lines.join('<br/>');
      },
    },
    toolbox: {
      right: 0,
      feature: { restore: { show: true }, saveAsImage: { show: true } },
    },
    xAxis: {
      type: 'time',
      axisTick: { show: false },
      axisLine: { lineStyle: { color: palette.grid } },
      axisLabel: { color: palette.axis, hideOverlap: true },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      min: percentage ? 0 : undefined,
      max: percentage ? 100 : undefined,
      interval: percentage ? 10 : undefined,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: palette.axis, formatter: `{value}${unit}` },
      splitLine: {
        show: true,
        lineStyle: { color: palette.grid, type: 'dotted', width: 1 },
      },
    },
    series: chartSeries,
  };

  if (pieces.length) {
    option.visualMap = {
      show: false,
      type: 'piecewise',
      dimension: 1,
      seriesIndex: 0,
      pieces,
    };
  }
  return option;
}
