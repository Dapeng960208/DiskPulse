import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('volume performance monitoring detail', () => {
  it('uses the dedicated monitoring page without the generic alert panel', () => {
    const detail = source('src/pages/admin/volume/VolumeDetailPage.vue');
    const page = source('src/pages/admin/volume/VolumeMonitoringPage.vue');

    expect(detail).toContain('VolumeMonitoringPage');
    expect(detail).not.toContain('RealTimePage');
    expect(page).toContain('fetchMonitoring');
    expect(page).not.toContain('alertApi');
  });

  it('defaults to three separate performance charts and keeps capacity independent', () => {
    const page = source('src/pages/admin/volume/VolumeMonitoringPage.vue');

    expect(page).toContain("['latency_total', 'iops_total', 'throughput_total']");
    expect(page).toContain('存储空间容量变化');
    expect(page).toContain('v-for="metric in selectedMetrics"');
    expect(page).toContain('performance-grid');
    expect(page).toContain('monitoring.value.performance || []');
    expect(page).toContain("capacity_unit: 'TB'");
    expect(page).toContain(':unit="capacityUnit"');
  });

  it('starts with the filter toolbar instead of a duplicate page header', () => {
    const page = source('src/pages/admin/volume/VolumeMonitoringPage.vue');

    expect(page).not.toContain('volume-monitoring-page__header');
    expect(page).not.toContain('存储空间性能监控');
    expect(page).not.toContain('查看存储空间容量变化和关联存储集群的实时性能指标。');
  });
});
