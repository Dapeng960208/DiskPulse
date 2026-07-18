import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = readFileSync(
  resolve(process.cwd(), 'src/pages/admin/storage-cluster/StorageClusterDetailPage.vue'),
  'utf8',
);

describe('StorageClusterDetailPage incident tab', () => {
  it('keeps related incidents as a lazy tab without altering existing alert semantics', () => {
    expect(source).toContain("defineAsyncComponent(() => import('./components/ClusterIncidentsTab.vue'))");
    expect(source).toContain('label="关联事件"');
    expect(source).toContain('v-if="activeTab === \'incidents\' && clusterId"');
  });
});
