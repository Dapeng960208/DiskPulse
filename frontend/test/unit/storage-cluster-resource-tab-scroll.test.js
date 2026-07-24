import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('storage cluster resource tab scrolling', () => {
  it('uses shared table scrolling while keeping the pager reachable', () => {
    const page = source('src/pages/admin/storage-cluster/StorageClusterDetailPage.vue');
    const resourceTab = source('src/pages/admin/storage-cluster/components/ClusterResourceListTab.vue');
    const distributionTab = source('src/pages/admin/storage-cluster/components/ClusterDistributionTab.vue');
    const dataTable = source('src/components/data/DataTable.vue');

    expect(page).toContain('class="storage-health-page__card"');
    expect(page).toContain('class="storage-health-page__tabs"');
    expect(page).toMatch(/\.storage-health-page__card \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    expect(page).toMatch(/\.storage-health-page__tabs \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    expect(page).toMatch(/\.storage-health-page__tabs :deep\(\.el-tabs__content\) \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  min-height: 0;\r?\n  overflow-x: hidden;\r?\n  overflow-y: auto;/);
    expect(page).toMatch(/\.storage-health-page__tabs :deep\(\.el-tab-pane\) \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    expect(resourceTab).toMatch(/\.cluster-resource-list-tab \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    expect(resourceTab).toMatch(/\.cluster-resource-list-tab :deep\(\.data-table-card\) \{\r?\n  flex: 1 1 auto;\r?\n  min-height: 0;\r?\n  height: auto;/);
    expect(distributionTab).toMatch(/\.analytics-chart-stage \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    expect(dataTable).toMatch(/\.table-wrapper \{\r?\n  flex: 1 1 auto;\r?\n  min-height: 0;\r?\n  overflow: auto;/);
    expect(dataTable.indexOf('class="pagination-bottom"'))
      .toBeGreaterThan(dataTable.indexOf('class="table-wrapper flex-1"'));
    expect(resourceTab).not.toMatch(/:deep\(\.table-wrapper\)/);
    expect(resourceTab).not.toMatch(/:deep\(\.el-table/);
  });
});
