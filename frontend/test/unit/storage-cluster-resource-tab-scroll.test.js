import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('storage cluster resource tab scrolling', () => {
  it('constrains detail tables to vertical scrolling while keeping the pager reachable', () => {
    const page = source('src/pages/admin/storage-cluster/StorageClusterDetailPage.vue');
    const resourceTab = source('src/pages/admin/storage-cluster/components/ClusterResourceListTab.vue');
    const dataTable = source('src/components/data/DataTable.vue');

    expect(page).toContain('class="storage-health-page__card"');
    expect(page).toContain('class="storage-health-page__tabs"');
    expect(page).toMatch(/\.storage-health-page__card \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    expect(page).toMatch(/\.storage-health-page__tabs \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    expect(page).toMatch(/\.storage-health-page__tabs :deep\(\.el-tabs__content\) \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  min-height: 0;\r?\n  overflow-x: hidden;\r?\n  overflow-y: auto;/);
    expect(page).toMatch(/\.storage-health-page__tabs :deep\(\.el-tab-pane\) \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    expect(resourceTab).toMatch(/\.cluster-resource-list-tab :deep\(\.data-table-card\) \{\r?\n  flex: 1 1 auto;\r?\n  min-height: 0;\r?\n  height: auto;/);
    expect(resourceTab).toMatch(/\.cluster-resource-list-tab :deep\(\.table-wrapper\) \{\r?\n  overflow-x: hidden;\r?\n  overflow-y: auto;/);
    expect(page).toMatch(/\.table-wrap \{\r?\n  max-width: 100%;\r?\n  overflow-x: hidden;\r?\n  overflow-y: auto;/);
    expect(page).toMatch(/\.storage-health-page :deep\(\.el-table__body-wrapper\) \{\r?\n  overflow-x: hidden !important;/);
    expect(page).toMatch(/\.analytics-chart-stage \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    expect(dataTable).toMatch(/\.table-wrapper \{\r?\n  flex: 1 1 auto;\r?\n  min-height: 0;\r?\n  overflow: auto;/);
  });
});
