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

  it('adds lazy, cluster-scoped resource tabs without replacing the standalone list pages', () => {
    expect(source).toContain("defineAsyncComponent(() => import('./components/ClusterResourceListTab.vue'))");
    expect(source).toContain('label="容量池"');
    expect(source).toContain('name="aggregates"');
    expect(source).toContain('resource-type="aggregate"');
    expect(source).toContain('label="存储空间"');
    expect(source).toContain('name="volumes"');
    expect(source).toContain('resource-type="volume"');
    expect(source).toContain('label="Qtree（NetApp）"');
    expect(source).toContain('name="qtrees"');
    expect(source).toContain('resource-type="qtree"');
    expect(source).toContain("infoResult?.storage_type !== 'isilon'");
    expect(source).not.toContain('AggregateListPage');
    expect(source).not.toContain('VolumeListPage');
    expect(source).not.toContain('QtreeListPage');
  });
});
