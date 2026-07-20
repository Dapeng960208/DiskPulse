import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('realtime page height contract', () => {
  it('keeps every realtime page consumer within the app content boundary', () => {
    const userDirectoryDetail = source('src/pages/usage/UsageDetailPage.vue');
    const groupDetail = source('src/pages/group/GroupDetailPage.vue');
    const aggregateDetail = source('src/pages/admin/aggregate/AggregateDetailPage.vue');
    const qtreeDetail = source('src/pages/admin/qtree/QtreeDetailPage.vue');

    expect(userDirectoryDetail).toContain(':fill-content="true"');
    expect(groupDetail).toContain(':fill-content="true"');
    expect(groupDetail).toMatch(/\.detail-monitor-page \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    expect(aggregateDetail).toContain(':fill-content="true"');
    expect(qtreeDetail).toContain(':fill-content="true"');
  });
});
