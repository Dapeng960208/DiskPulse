import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const timeRangePages = [
  'src/pages/common/RealTimePage.vue',
  'src/pages/admin/storage-cluster/components/ClusterCapacityTab.vue',
  'src/pages/admin/storage-cluster/components/ClusterPerformanceTab.vue',
  'src/pages/admin/storage-cluster/components/ClusterFaultsTab.vue',
  'src/pages/admin/volume/VolumeMonitoringPage.vue',
  'src/pages/admin/audit/AuditEventListPage.vue',
];

describe('time range picker coverage', () => {
  it.each(timeRangePages)('%s delegates range selection to the shared TimeRangePicker', (path) => {
    const source = readFileSync(resolve(process.cwd(), path), 'utf8');

    expect(source).toContain("import TimeRangePicker from '@/components/form/TimeRangePicker.vue';");
    expect(source).toContain('<TimeRangePicker');
    expect(source).not.toContain('<ElDatePicker');
  });
});
